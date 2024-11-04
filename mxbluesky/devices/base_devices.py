from ophyd.pv_positioner import PVPositioner
from ophyd import Component as Cpt
from ophyd.signal import Signal
from ophyd.utils import ReadOnlyError
import numpy as np
from typing import Optional

# Note: These signals and devices are available in the latest versions of ophyd
# The reason its copied here is because LSDC GUI uses python 3.6 and ophyd needs
# python >= 3.8. Can safely be deleted once LSDC python is upgraded


class InternalSignalMixin:
    """
    Mix-in class for adding the `InternalSignal` behavior to any signal class.

    A signal class with this mixin will reject all sets and puts unless
    internal=True is passed as an argument.

    The intended use for this is to signify that a signal is for internal use
    by the class only. That is, it would be a mistake to try to cause puts to
    this signal by code external to the Device class.

    Some more concrete use-cases would be things like soft "status" type
    signals that should be read-only except that the class needs to edit it,
    or EPICS signals that should be written to by the class but are likely to
    cause issues for external writes due to behavior complexity.
    """

    def put(self, *args, internal: bool = False, **kwargs):
        """
        Write protection for an internal signal.

        This method is not intended to be used from outside of the device
        that defined this signal. All writes must be done with internal=True.
        """
        if not internal:
            raise InternalSignalError()
        return super().put(*args, **kwargs)

    def set(self, *args, internal: bool = False, **kwargs):
        """
        Write protection for an internal signal.

        This method is not intended to be used from outside of the device
        that defined this signal. All writes must be done with internal=True.
        """
        if not internal:
            raise InternalSignalError()
        return super().set(*args, internal=internal, **kwargs)


class InternalSignal(InternalSignalMixin, Signal):
    """
    A soft Signal that stores data but should only be updated by the Device.

    Unlike SignalRO, which will unilaterally block all writes, this will
    allow writes with internal=True.

    The intended use for this is to signify that a signal is for internal use
    by the class only. That is, it would be a mistake to try to cause puts to
    this signal by code external to the Device class.

    Some more concrete use-cases would be things like soft "status" type
    signals that should be read-only except that the class needs to edit it,
    or calculated "done" signals for positioner classes.
    """


class InternalSignalError(ReadOnlyError):
    """
    A read-only error sourced from trying to write to an internal signal.
    """

    def __init__(self, message=None):
        if message is None:
            message = (
                "This signal is for internal use only. "
                "You should not be writing to it from outside "
                "the parent class. If you do need to write to "
                "this signal, you can use signal.put(value, internal=True)."
            )
        super().__init__(message)


class PVPositionerComparator(PVPositioner):
    """
    PV Positioner with a software done signal.

    The done state is set by a comparison function defined in the class body.
    The comparison function takes two arguments, readback and setpoint,
    returning True if we are considered done or False if we are not.

    This class is intended to support `PVPositionerIsClose`, but exists to
    allow some flexibility if we want to use other metrics for deciding if
    the PVPositioner is done.

    Internally, this will subscribe to both the ``setpoint`` and ``readback``
    signals, updating ``done`` as appropriate.

    Parameters
    ----------
    prefix : str, optional
        The device prefix used for all sub-positioners. This is optional as it
        may be desirable to specify full PV names for PVPositioners.
    limits : 2-element sequence, optional
        (low_limit, high_limit)
    name : str
        The device name
    egu : str, optional
        The engineering units (EGU) for the position
    settle_time : float, optional
        The amount of time to wait after moves to report status completion
    timeout : float, optional
        The default timeout to use for motion requests, in seconds.

    Attributes
    ----------
    setpoint : Signal
        The setpoint (request) signal
    readback : Signal or None
        The readback PV (e.g., encoder position PV)
    actuate : Signal or None
        The actuation PV to set when movement is requested
    actuate_value : any, optional
        The actuation value, sent to the actuate signal when motion is
        requested
    stop_signal : Signal or None
        The stop PV to set when motion should be stopped
    stop_value : any, optional
        The value sent to stop_signal when a stop is requested
    put_complete : bool, optional
        If set, the specified PV should allow for asynchronous put completion
        to indicate motion has finished.  If ``actuate`` is specified, it will be
        used for put completion.  Otherwise, the ``setpoint`` will be used.  See
        the `-c` option from ``caput`` for more information.
    """

    done = Cpt(InternalSignal, value=0)
    done_value = 1

    def __init__(self, prefix: str, *, name: str, **kwargs):
        self._last_readback = None
        self._last_setpoint = None
        super().__init__(prefix, name=name, **kwargs)
        if None in (self.setpoint, self.readback):
            raise NotImplementedError(
                "PVPositionerComparator requires both "
                "a setpoint and a readback signal to "
                "compare!"
            )

    def __init_subclass__(cls, **kwargs):
        """Set up callbacks in subclass."""
        super().__init_subclass__(**kwargs)
        if None not in (cls.setpoint, cls.readback):
            cls.setpoint.sub_value(cls._update_setpoint)
            cls.readback.sub_value(cls._update_readback)

    def done_comparator(self, readback: Any, setpoint: Any) -> bool:
        """
        Override done_comparator in your subclass.

        This method should return True if we are done moving
        and False otherwise.
        """
        raise NotImplementedError("Must implement a done comparator!")

    def _update_setpoint(self, *args, value: Any, **kwargs) -> None:
        """Callback to cache the setpoint and update done state."""
        self._last_setpoint = value
        # Always set done to False when a move is requested
        # This means we always get a rising edge when finished moving
        # Even if the move distance is under our done moving tolerance
        self.done.put(0, internal=True)
        self._update_done()

    def _update_readback(self, *args, value: Any, **kwargs) -> None:
        """Callback to cache the readback and update done state."""
        self._last_readback = value
        self._update_done()

    def _update_done(self) -> None:
        """Update our status to done if we pass the comparator."""
        if None not in (self._last_readback, self._last_setpoint):
            is_done = self.done_comparator(self._last_readback, self._last_setpoint)
            done_value = int(is_done)
            if done_value != self.done.get():
                self.done.put(done_value, internal=True)


class PVPositionerIsClose(PVPositionerComparator):
    """
    PV Positioner that updates done state based on np.isclose.

    Effectively, this will treat our move as complete if the readback is
    sufficiently close to the setpoint. This is generically helpful for
    PV positioners that don't have a ``done`` signal built into the hardware.

    The arguments atol and rtol can be set as class attributes or passed as
    initialization arguments.

    atol is a measure of absolute tolerance. If atol is 0.1, then you'd be
    able to be up to 0.1 units away and still count as done. This is
    typically the most useful parameter for calibrating done tolerance.

    rtol is a measure of relative tolerance. If rtol is 0.1, then you'd be
    able to deviate from the goal position by up to 10% of its value. This
    is useful for small quantities. For example, defining an atol for a
    positioner that ranges from 1e-8 to 2e-8 could be somewhat awkward.

    Parameters
    ----------
    prefix : str, optional
        The device prefix used for all sub-positioners. This is optional as it
        may be desirable to specify full PV names for PVPositioners.
    limits : 2-element sequence, optional
        (low_limit, high_limit)
    name : str
        The device name
    egu : str, optional
        The engineering units (EGU) for the position
    settle_time : float, optional
        The amount of time to wait after moves to report status completion
    timeout : float, optional
        The default timeout to use for motion requests, in seconds.
    atol : float, optional
        A measure of absolute tolerance. If atol is 0.1, then you'd be
        able to be up to 0.1 units away and still count as done.
    rtol : float, optional
        A measure of relative tolerance. If rtol is 0.1, then you'd be
        able to deviate from the goal position by up to 10% of its value

    Attributes
    ----------
    setpoint : Signal
        The setpoint (request) signal
    readback : Signal or None
        The readback PV (e.g., encoder position PV)
    actuate : Signal or None
        The actuation PV to set when movement is requested
    actuate_value : any, optional
        The actuation value, sent to the actuate signal when motion is
        requested
    stop_signal : Signal or None
        The stop PV to set when motion should be stopped
    stop_value : any, optional
        The value sent to stop_signal when a stop is requested
    put_complete : bool, optional
        If set, the specified PV should allow for asynchronous put completion
        to indicate motion has finished.  If ``actuate`` is specified, it will be
        used for put completion.  Otherwise, the ``setpoint`` will be used.  See
        the `-c` option from ``caput`` for more information.
    atol : float, optional
        A measure of absolute tolerance. If atol is 0.1, then you'd be
        able to be up to 0.1 units away and still count as done.
    rtol : float, optional
        A measure of relative tolerance. If rtol is 0.1, then you'd be
        able to deviate from the goal position by up to 10% of its value
    """

    atol: Optional[float] = None
    rtol: Optional[float] = None

    def __init__(
        self,
        prefix: str,
        *,
        name: str,
        atol: Optional[float] = None,
        rtol: Optional[float] = None,
        **kwargs,
    ):
        if atol is not None:
            self.atol = atol
        if rtol is not None:
            self.rtol = rtol
        super().__init__(prefix, name=name, **kwargs)

    def done_comparator(self, readback: float, setpoint: float) -> bool:
        """
        Check if the readback is close to the setpoint value.

        Uses numpy.isclose to make the comparison. Tolerance values
        atol and rtol for numpy.isclose are taken from the attributes
        self.atol and self.rtol, which can be defined as class attributes
        or passed in as init parameters.

        If atol or rtol are omitted, the default values from numpy are
        used instead.
        """
        kwargs = {}
        if self.atol is not None:
            kwargs["atol"] = self.atol
        if self.rtol is not None:
            kwargs["rtol"] = self.rtol
        return np.isclose(readback, setpoint, **kwargs)
