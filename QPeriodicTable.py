#/*##########################################################################
# Copyright (C) 2004-2013 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
#
# This toolkit is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# PyMca is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# PyMca; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# PyMca follows the dual licensing model of Riverbank's PyQt and cannot be
# used as a free plugin for a non-free program.
#
# Please contact the ESRF industrial unit (industry@esrf.fr) if this license
# is a problem for you.
#############################################################################*/
import sys
from PyMca.PyMcaQt import *
from element_info import element_info #skinner, from nsls-I

QTVERSION = qVersion()
if QTVERSION < '4.0.0':
    import qttable
    QComboTableItem = qttable.QComboTableItem
    MyQListView = QListView
else:
    qttable = QTableWidget
    QComboTableItem = QComboBox
    MyQListView = QTreeWidget
    QListViewItem = QTreeWidgetItem
#
#   Symbol  Atomic Number   x y ( positions on table )
#       name,  mass, density 
#
DEBUG = 0

Elements = [
   ["H",   1,    1,1,   "hydrogen",   1.00800,     1008.00   ],
   ["He",  2,   18,1,   "helium",     4.00300,     0.118500  ],
   ["Li",  3,    1,2,   "lithium",    6.94000,     534.000   ],
   ["Be",  4,    2,2,   "beryllium",  9.01200,     1848.00   ],
   ["B",   5,   13,2,   "boron",      10.8110,     2340.00   ],
   ["C",   6,   14,2,   "carbon",     12.0100,     1580.00   ],
   ["N",   7,   15,2,   "nitrogen",   14.0080,     1.25      ],
   ["O",   8,   16,2,   "oxygen",     16.0000,     1.429     ],
   ["F",   9,   17,2,   "fluorine",   19.0000,     1108.00   ],
   ["Ne",  10,  18,2,   "neon",       20.1830,     0.9       ],
   ["Na",  11,   1,3,   "sodium",     22.9970,     970.000   ],
   ["Mg",  12,   2,3,   "magnesium",  24.3200,     1740.00   ],
   ["Al",  13,  13,3,   "aluminium",  26.9700,     2720.00   ],
   ["Si",  14,  14,3,   "silicon",    28.0860,     2330.00   ],
   ["P",   15,  15,3,   "phosphorus", 30.9750,     1820.00   ],
   ["S",   16,  16,3,   "sulphur",    32.0660,     2000.00   ],
   ["Cl",  17,  17,3,   "chlorine",   35.4570,     1560.00   ],
   ["Ar",  18,  18,3,   "argon",      39.9440,     1.78400   ],
   ["K",   19,   1,4,   "potassium",  39.1020,     862.000   ],
   ["Ca",  20,   2,4,   "calcium",    40.0800,     1550.00   ],
   ["Sc",  21,   3,4,   "scandium",   44.9600,     2992.00   ],
   ["Ti",  22,   4,4,   "titanium",   47.9000,     4540.00   ],
   ["V",   23,   5,4,   "vanadium",   50.9420,     6110.00   ],
   ["Cr",  24,   6,4,   "chromium",   51.9960,     7190.00   ],
   ["Mn",  25,   7,4,   "manganese",  54.9400,     7420.00   ],
   ["Fe",  26,   8,4,   "iron",       55.8500,     7860.00   ],
   ["Co",  27,   9,4,   "cobalt",     58.9330,     8900.00   ],
   ["Ni",  28,  10,4,   "nickel",     58.6900,     8900.00   ],
   ["Cu",  29,  11,4,   "copper",     63.5400,     8940.00   ],
   ["Zn",  30,  12,4,   "zinc",       65.3800,     7140.00   ],
   ["Ga",  31,  13,4,   "gallium",    69.7200,     5903.00   ],
   ["Ge",  32,  14,4,   "germanium",  72.5900,     5323.00   ],
   ["As",  33,  15,4,   "arsenic",    74.9200,     5730.00   ],
   ["Se",  34,  16,4,   "selenium",   78.9600,     4790.00   ],
   ["Br",  35,  17,4,   "bromine",    79.9200,     3120.00   ],
   ["Kr",  36,  18,4,   "krypton",    83.8000,     3.74000   ],
   ["Rb",  37,   1,5,   "rubidium",   85.4800,     1532.00   ],
   ["Sr",  38,   2,5,   "strontium",  87.6200,     2540.00   ],
   ["Y",   39,   3,5,   "yttrium",    88.9050,     4405.00   ],
   ["Zr",  40,   4,5,   "zirconium",  91.2200,     6530.00   ],
   ["Nb",  41,   5,5,   "niobium",    92.9060,     8570.00   ],
   ["Mo",  42,   6,5,   "molybdenum", 95.9500,     10220.00  ],
   ["Tc",  43,   7,5,   "technetium", 99.0000,     11500.0   ],
   ["Ru",  44,   8,5,   "ruthenium",  101.0700,    12410.0   ],
   ["Rh",  45,   9,5,   "rhodium",    102.9100,    12440.0   ],
   ["Pd",  46,  10,5,   "palladium",  106.400,     12160.0   ],
   ["Ag",  47,  11,5,   "silver",     107.880,     10500.00  ],
   ["Cd",  48,  12,5,   "cadmium",    112.410,     8650.00   ],
   ["In",  49,  13,5,   "indium",     114.820,     7280.00   ],
   ["Sn",  50,  14,5,   "tin",        118.690,     5310.00   ],
   ["Sb",  51,  15,5,   "antimony",   121.760,     6691.00   ],
   ["Te",  52,  16,5,   "tellurium",  127.600,     6240.00   ],
   ["I",   53,  17,5,   "iodine",     126.910,     4940.00   ],
   ["Xe",  54,  18,5,   "xenon",      131.300,     5.90000   ],
   ["Cs",  55,   1,6,   "caesium",    132.910,     1873.00   ],
   ["Ba",  56,   2,6,   "barium",     137.360,     3500.00   ],
   ["La",  57,   3,6,   "lanthanum",  138.920,     6150.00   ],
   ["Ce",  58,   4,9,   "cerium",     140.130,     6670.00   ],
   ["Pr",  59,   5,9,   "praseodymium",140.920,    6769.00   ],
   ["Nd",  60,   6,9,   "neodymium",  144.270,     6960.00   ],
   ["Pm",  61,   7,9,   "promethium", 147.000,     6782.00   ],
   ["Sm",  62,   8,9,   "samarium",   150.350,     7536.00   ],
   ["Eu",  63,   9,9,   "europium",   152.000,     5259.00   ],
   ["Gd",  64,  10,9,   "gadolinium", 157.260,     7950.00   ],
   ["Tb",  65,  11,9,   "terbium",    158.930,     8272.00   ],
   ["Dy",  66,  12,9,   "dysprosium", 162.510,     8536.00   ],
   ["Ho",  67,  13,9,   "holmium",    164.940,     8803.00   ],
   ["Er",  68,  14,9,   "erbium",     167.270,     9051.00   ],
   ["Tm",  69,  15,9,   "thulium",    168.940,     9332.00   ],
   ["Yb",  70,  16,9,   "ytterbium",  173.040,     6977.00   ],
   ["Lu",  71,  17,9,   "lutetium",   174.990,     9842.00   ],
   ["Hf",  72,   4,6,   "hafnium",    178.500,     13300.0   ],
   ["Ta",  73,   5,6,   "tantalum",   180.950,     16600.0   ],
   ["W",   74,   6,6,   "tungsten",   183.920,     19300.0   ],
   ["Re",  75,   7,6,   "rhenium",    186.200,     21020.0   ],
   ["Os",  76,   8,6,   "osmium",     190.200,     22500.0   ],
   ["Ir",  77,   9,6,   "iridium",    192.200,     22420.0   ],
   ["Pt",  78,  10,6,   "platinum",   195.090,     21370.0   ],
   ["Au",  79,  11,6,   "gold",       197.200,     19370.0   ],
   ["Hg",  80,  12,6,   "mercury",    200.610,     13546.0   ],
   ["Tl",  81,  13,6,   "thallium",   204.390,     11860.0   ],
   ["Pb",  82,  14,6,   "lead",       207.210,     11340.0   ],
   ["Bi",  83,  15,6,   "bismuth",    209.000,     9800.00   ],
   ["Po",  84,  16,6,   "polonium",   209.000,     0         ],
   ["At",  85,  17,6,   "astatine",   210.000,     0         ],
   ["Rn",  86,  18,6,   "radon",      222.000,     9.73000   ],
   ["Fr",  87,   1,7,   "francium",   223.000,     0         ],
   ["Ra",  88,   2,7,   "radium",     226.000,     0         ],
   ["Ac",  89,   3,7,   "actinium",   227.000,     0         ],
   ["Th",  90,   4,10,  "thorium",    232.000,     11700.0   ],
   ["Pa",  91,   5,10,  "proactinium",231.03588,   0         ],
   ["U",   92,   6,10,  "uranium",    238.070,     19050.0   ],
   ["Np",  93,   7,10,  "neptunium",  237.000,     0         ],
   ["Pu",  94,   8,10,  "plutonium",  239.100,     19700.0   ],
   ["Am",  95,   9,10,  "americium",  243,         0         ],
   ["Cm",  96,  10,10,  "curium",     247,         0         ],
   ["Bk",  97,  11,10,  "berkelium",  247,         0         ],
   ["Cf",  98,  12,10,  "californium",251,         0         ],
   ["Es",  99,  13,10,  "einsteinium",252,         0         ],
   ["Fm",  100,  14,10, "fermium",    257,         0         ],
   ["Md",  101,  15,10, "mendelevium",258,         0         ],
   ["No",  102,  16,10, "nobelium",   259,         0         ],
   ["Lr",  103,  17,10, "lawrencium", 262,         0         ],
   ["Rf",  104,   4,7,  "rutherfordium",261,       0         ],
   ["Db",  105,   5,7,  "dubnium",    262,         0         ],
   ["Sg",  106,   6,7,  "seaborgium", 266,         0         ],
   ["Bh",  107,   7,7,  "bohrium",    264,         0         ],
   ["Hs",  108,   8,7,  "hassium",    269,         0         ],
   ["Mt",  109,   9,7,  "meitnerium", 268,         0         ],
]
ElementList= [ elt[0] for elt in Elements ]

class ElementButton(QPushButton):
    def __init__(self, parent, symbol, Z, name):
        if QTVERSION < '4.0.0':
            QPushButton.__init__(self, parent, symbol)
        else:
            QPushButton.__init__(self, parent)
            
        self.symbol = symbol
        self.Z      = Z
        self.name   = name

        self.setText(symbol)
        self.setFlat(1)
        if QTVERSION < '4.0.0':
            self.setToggleButton(0)
        else:
            self.setCheckable(0)

#        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

        self.selected= 0
        self.current= 0
        self.colors= [ QColor(Qt.yellow), QColor(Qt.darkYellow), QColor(Qt.gray) ]
        if QTVERSION < '4.0.0':
            self.brush = None
        else:
            self.brush= QBrush()

        self.connect(self, SIGNAL("clicked()"), self.clickedSlot)

    if QTVERSION > '4.3.0':
        def sizeHint(self):
            return QSize(40, 40)

    def setCurrent(self, b):
        self.current= b
        self.__setBrush()

    def isCurrent(self):
        return self.current

    def isSelected(self):
        return self.selected

    def setSelected(self, b):
        self.selected= b
        self.__setBrush()

    def __setBrush(self):
        if QTVERSION < '4.0.0':
            if self.current and self.selected:
                self.brush= QBrush(self.colors[1])
            elif self.selected:
                self.brush= QBrush(self.colors[0])
            elif self.current:
                self.brush= QBrush(self.colors[2])
            else:
                self.brush= None
            self.update()
        else:
            role = self.backgroundRole()
            palette = self.palette()
            if self.current and self.selected:
                self.brush= QBrush(self.colors[1])
            elif self.selected:
                self.brush= QBrush(self.colors[0])
            elif self.current:
                self.brush= QBrush(self.colors[2])
            else:
                self.brush= QBrush()
            palette.setBrush( role,self.brush)
            self.update()


    def paintEvent(self, pEvent):
        if QTVERSION < '4.0.0':
            QPushButton.paintEvent(self, pEvent)
        else:
            p = QPainter(self)
            wr= self.rect()
            pr= QRect(wr.left()+1, wr.top()+1, wr.width()-2, wr.height()-2)
            if self.brush is not None:
                p.fillRect(pr, self.brush)
            p.setPen(Qt.black)
            p.drawRect(pr)
            p.end()
            QPushButton.paintEvent(self, pEvent)
        
    def drawButton(self, p):
        #Qt 2 and Qt3
        wr= self.rect()
        pr= QRect(wr.left()+1, wr.top()+1, wr.width()-2, wr.height()-2)
        if self.brush is not None:
            p.fillRect(pr, self.brush)
        QPushButton.drawButtonLabel(self, p)
        p.setPen(Qt.black)
        p.drawRect(pr)

    def enterEvent(self, e):
        if QTVERSION < '4.0.0':
            self.emit(PYSIGNAL("elementEnter"), (self.symbol,self.Z,self.name))
        else:
            self.emit(SIGNAL("elementEnter"),
                              self.symbol, self.Z,
                              self.name)
            
    def leaveEvent(self, e):
        if QTVERSION < '4.0.0':
            self.emit(PYSIGNAL("elementLeave"), (self.symbol,))
        else:
            self.emit(SIGNAL("elementLeave"), self.symbol)

    def clickedSlot(self):
        if QTVERSION < '4.0.0':
            self.emit(PYSIGNAL("elementClicked"), (self.symbol,))
        else:
            self.emit(SIGNAL("elementClicked"), self.symbol)


class QPeriodicTable(QWidget):
    """ Periodic Table - Qt version
        Public methods:
            setSelection(eltlist):
                set all elements in eltlist selected
                if mode single, set last element of eltlist selected
            getSelection():
                get list of selected elements

        Signal (PYSIGNAL):
            elementClicked(symbol):
    """
    def __init__(self, parent=None, name="PeriodicTable", fl=0,butSize=0):
        self.butSize = butSize
        if QTVERSION < '4.0.0': 
            QWidget.__init__(self,parent,name,fl)
            self.setName(name)
            self.setCaption("QPeriodicTable")
            self.gridLayout= QGridLayout(self, 6, 10, 0, 0, "PTLayout")
            self.gridLayout.addRowSpacing(7, 5)
        else:
            QWidget.__init__(self,parent)
            self.setWindowTitle(name)
            self.gridLayout= QGridLayout(self)
            self.gridLayout.setMargin(0)
            #, 6, 10, 0, 0, "PTLayout")
            self.gridLayout.addItem(QSpacerItem(0, 5), 7, 0)

        for idx in range(10):
            self.gridLayout.setRowStretch(idx, 3)
        self.gridLayout.setRowStretch(7, 2)

        self.eltLabel= QLabel(self)
        f= self.eltLabel.font()
        f.setBold(1)
        self.eltLabel.setFont(f)
        self.eltLabel.setAlignment(Qt.AlignHCenter)
        if QTVERSION < '4.0.0':
            self.gridLayout.addMultiCellWidget(self.eltLabel, 1, 1, 3, 10)
        else:
            self.gridLayout.addWidget(self.eltLabel, 1, 1, 3, 10)

        self.eltCurrent= None
        self.eltButton= {}
        for (symbol, Z, x, y, name, mass, density) in Elements:
            self.__addElement(symbol, Z, name, y-1, x-1)


    def __addElement(self, symbol, Z, name, row, col):
        b= ElementButton(self, symbol, Z, name)
        if (self.butSize > 0): #skinner - use a fixed size
          b.setFixedSize(self.butSize,self.butSize)
        b.setAutoDefault(False)
        if (element_info.has_key(symbol) and element_info[symbol][4] > 0):
          b.setEnabled(True)
        else:
          b.setEnabled(False)
        self.eltButton[symbol]= b
        self.gridLayout.addWidget(b, row, col)
        if QTVERSION <'4.0.0':
            QObject.connect(b, PYSIGNAL("elementEnter"), self.elementEnter)
            QObject.connect(b, PYSIGNAL("elementLeave"), self.elementLeave)
            QObject.connect(b, PYSIGNAL("elementClicked"), self.elementClicked)
        else:
            QObject.connect(b, SIGNAL(("elementEnter")), self.elementEnter)
            QObject.connect(b, SIGNAL("elementLeave"), self.elementLeave)
            QObject.connect(b, SIGNAL("elementClicked"), self.elementClicked)

    def elementEnter(self, symbol, z, name):
        self.eltLabel.setText("%s(%d) - %s"%(symbol, z, name))

    def elementLeave(self, symbol):
        self.eltLabel.setText("")

    def elementClicked(self, symbol):
        if self.eltCurrent is not None:
            self.eltCurrent.setCurrent(0)
        if QTVERSION > '4.0.0': symbol = str(symbol)
        self.eltButton[symbol].setCurrent(1)
        self.eltCurrent= self.eltButton[symbol]
        if QTVERSION < '4.0.0':
            self.emit(PYSIGNAL("elementClicked"), (symbol,))
        else:
            self.emit(SIGNAL("elementClicked"), symbol)
        print(self.eltCurrent.symbol)
        print(self.eltButton[symbol].isSelected())                        
            
            
    def getSelection(self):
        return [ e for (e,b) in self.eltButton.items() if b.isSelected() ]

    def setSelection(self, symbolList):
        for (e,b) in self.eltButton.items():
            b.setSelected(e in symbolList)

    def setElementSelected(self, symbol, state):
        self.eltButton[symbol].setSelected(state)

    def isElementSelected(self, symbol):
        return self.eltButton[symbol].isSelected()

    def elementToggle(self, symbol):
        if QTVERSION > '4.0.0':symbol = str(symbol)
        b= self.eltButton[symbol]
        b.setSelected(not b.isSelected())

class QPeriodicComboTableItem(QComboTableItem):
    """ Periodic Table Combo List to be used in a QTable
        Init options:
            table (mandatory)= parent QTable
            addnone= 1 (default) add "-" in the list to provide possibility
                        to select no specific element.
                 0 only element list.
            detailed= 1 (default) display element symbol, Z and name
                  0 display only element symbol and Z
        Public methods:
            setSelection(eltsymbol):
                Set the element selected given its symbol
            getSelection():
                Return symbol of element selected

        Signals:
            No specific signals. Use signals from QTable
            SIGNAL("valueChanged(int,int)") for example.
    """
    def __init__(self, table, addnone=1, detailed=0):
        strlist= QStringList()
        self.addnone= (addnone==1)
        if self.addnone: strlist.append("-")
        for (symbol, Z, x, y, name, mass, density) in Elements:
            if detailed:    txt= "%2s (%d) - %s"%(symbol, Z, name)
            else:       txt= "%2s (%d)"%(symbol, Z)
            strlist.append(txt)
        if QTVERSION < '4.0.0':
            QComboTableItem.__init__(self, table, strlist)
        else:
            QComboBox.__init__(self)
            self.addItems(strlist)
            print("still to continue")

    def setSelection(self, symbol=None):
        if symbol is None:
            if self.addnone: self.setCurrentItem(0)
        else:
            idx= self.addnone+ElementList[symbol]
            self.setCurrentItem(idx)

    def getSelection(self):
        id= self.currentItem()
        if self.addnone and not id: return None
        else: return ElementList[id-self.addnone]
        
class QPeriodicCombo(QComboBox):
    """ Periodic Table Element list in a QComboBox
        Init options:
            detailed= 1 (default) display element symbol, Z and name
                  0 display only element symbol and Z
        Public methods:
            setSelection(eltsymbol):
                Set the element selected given its symbol
            getSelection():
                Return symbol of element selected

        Signal (PYSIGNAL):
            selectionChanged(elt):
                signal sent when the selection changed
                send symbol of element selected
    """
    def __init__(self, parent=None, name=None, detailed=1):
        if QTVERSION < '4.0.0':
            QComboBox.__init__(self, parent, name)
        else:
            QComboBox.__init__(self, parent)

        i = 0
        for (symbol, Z, x, y, name, mass, density) in Elements:
            if detailed:    txt= "%2s (%d) - %s"%(symbol, Z, name)
            else:       txt= "%2s (%d)"%(symbol, Z)
            if QTVERSION < '4.0.0': self.insertItem(txt)
            else: self.insertItem(i,txt)
            i += 1
            
        self.connect(self, SIGNAL("activated(int)"), self.__selectionChanged)

    def __selectionChanged(self, idx):
        if QTVERSION < '4.0.0':
            self.emit(PYSIGNAL("selectionChanged"), (Elements[idx][0],))
        else:
            self.emit(SIGNAL("selectionChanged"), Elements[idx][0])

    def getSelection(self):
        return Elements[self.currentItem()]

    def setSelection(self, symbol):
        symblist= [ elt[0] for elt in Elements ]
        self.setCurrentItem(symblist.index(symbol))
        

class QPeriodicList(MyQListView):
    """ Periodic Table Element list in a QListView
        Init options:
            detailed= 1 (default) display element symbol, Z and name
                  0 display only element symbol and Z
            single= 1 for single element selection mode
                0 (default) for multi element selection mode
        Public methods:
            setSelection(symbollist):
                Set the list of symbol selected
            getSelection():
                Return the list of symbol selected

        Signal (PYSIGNAL):
            selectionChanged(elt):
                signal sent when the selection changed
                send list of symbol selected
    """
    def __init__(self, master=None, name=None, fl=0, detailed=1, single=0):
        if QTVERSION < '4.0.0':
            MyQListView.__init__(self, master, name, fl)
        else:
            MyQListView.__init__(self, master)

    
        self.detailed= (detailed==1)    

        if QTVERSION < '4.0.0':
            self.addColumn("Z")
            self.addColumn("Symbol")
            if detailed: self.addColumn("Name")
            self.header().setClickEnabled(0, -1)
            self.setAllColumnsShowFocus(1)
            self.setSelectionMode((single and QListView.Single) or QListView.Extended)
            self.setSorting(-1)
            self.connect(self, SIGNAL("selectionChanged()"), self.__selectionChanged)
            self.__fill_list()
        else:
            try:
                strlist= QStringList()
            except:
                strlist= []
            strlist.append("Z")
            strlist.append("Symbol")
            if detailed:
                strlist.append("Name")
                self.setColumnCount(3)
            else:
                self.setColumnCount(2)
            self.setHeaderLabels(strlist)
            self.header().setStretchLastSection(False)
            self.setRootIsDecorated(0)
            self.connect(self, SIGNAL("itemSelectionChanged()"), self.__selectionChanged)
            print("what to do? ")
            """
            self.header().setClickEnabled(0, -1)
            self.setAllColumnsShowFocus(1)
            self.setSelectionMode((single and QListView.Single) or QListView.Extended)
            self.setSorting(-1)
            """
            self.setSelectionMode((single and QAbstractItemView.SingleSelection) or QAbstractItemView.ExtendedSelection)
            self.__fill_list()
            self.resizeColumnToContents(0)
            self.resizeColumnToContents(1)
            if detailed: self.resizeColumnToContents(2)


    def __fill_list(self):
        self.items= []
        after= None
        for (symbol, Z, x, y, name, mass, density) in Elements:
            if after is None: item= QListViewItem(self)
            else: item= QListViewItem(self, after)
            item.setText(0, str(Z))
            item.setText(1, symbol)
            if self.detailed:
                item.setText(2, name)
            self.items.append(item)
            if QTVERSION < '4.0.0':
                self.insertItem(item)
            after= item
    """
    def __selectionChanged(self):
        self.emit(PYSIGNAL("selectionChanged"), (self.getSelection(),))
    
    def getSelection(self):
        return [ Elements[idx][0] for idx in range(len(self.items)) if self.items[idx].isSelected() ]   

    def setSelection(self, symbolList):
        for idx in range(len(self.items)):
            self.items[idx].setSelected(Elements[idx][0] in symbolList)
    """
    def __selectionChanged(self):
        if QTVERSION < "4.0.0":
            self.emit(PYSIGNAL("selectionChanged"), (self.getSelection(),))
        else:
            self.emit(SIGNAL("selectionChanged"), self.getSelection())
    
    def getSelection(self):
        if QTVERSION < "4.0.0":
            return [ Elements[idx][0] for idx in range(len(self.items)) \
                    if self.items[idx].isSelected() ]
        else:
            return [ Elements[idx][0] for idx in range(len(self.items)) \
                    if self.isItemSelected(self.items[idx]) ]
            
            #return self.selectedItems()

    if QTVERSION < "4.0.0":
        def setSelection(self, symbolList):
            for idx in range(len(self.items)):
                if QTVERSION < "4.0.0":
                    self.items[idx].setSelected(Elements[idx][0] in symbolList)


def testwidget():
    def change(list):
        print("New selection:", list)

    a = QApplication(sys.argv)
    QObject.connect(a,SIGNAL("lastWindowClosed()"),a, SLOT("quit()"))

    w = QTabWidget()

    if QTVERSION < '4.0.0':
        f = QPeriodicTable(w)
    else:
        f = QPeriodicTable()
    if QTVERSION < '4.0.0':
        o= QWidget(w)
        ol= QVBoxLayout(o)
        #ol.setAutoAdd(1)
        tlabel = QLabel("QPeriodicCombo", o)
        ol.addWidget(tlabel)
        c = QPeriodicCombo(o)
        ol.addWidget(c)
        
        t = QLabel("QPeriodicList", o)
        ol.addWidget(t)
        l = QPeriodicList(o)
        ol.addWidget(l)
    else:
        o= QWidget()
        ol= QVBoxLayout(o)
        #ol.setAutoAdd(1)
        tlabel = QLabel("QPeriodicCombo", o)
        ol.addWidget(tlabel)
        c = QPeriodicCombo(o)
        ol.addWidget(c)
        
        t = QLabel("QPeriodicList", o)
        ol.addWidget(t)
        l = QPeriodicList(o)
        ol.addWidget(l)        

    if QTVERSION < '4.0.0':
        tab = qttable.QTable(w)
        tab.setNumRows(2)
        tab.setNumCols(1)
        tab.setItem(0, 0, QPeriodicComboTableItem(tab, addnone=0))
        tab.setItem(1, 0, QPeriodicComboTableItem(tab))
    else:
        tab = QTableWidget()
        tab.setRowCount(2)
        tab.setColumnCount(1)
        tab.setCellWidget(0, 0, QPeriodicCombo(tab, detailed=0))
        tab.setCellWidget(1, 0, QPeriodicCombo(tab, detailed=0))
        
    w.addTab(f, "QPeriodicTable")
    if QTVERSION < '4.0.0':
        w.addTab(o, "QPeriodicList/Combo")
        w.addTab(tab, "QPeriodicComboTableItem")
    else:
        w.addTab(o, "QPeriodicList/Combo")
        w.addTab(tab, "QPeriodicComboTableItem")
        

    f.setSelection(['H', 'Fe', 'Si'])
    
    if QTVERSION < '4.0.0':
        QObject.connect(f, PYSIGNAL("elementClicked"), f.elementToggle)
        QObject.connect(l, PYSIGNAL("selectionChanged"), change)
        QObject.connect(c, PYSIGNAL("selectionChanged"), change)
    else:
        QObject.connect(f, SIGNAL("elementClicked"), f.elementToggle)
        QObject.connect(l, SIGNAL("selectionChanged"), change)
        QObject.connect(c, SIGNAL("selectionChanged"), change)

    if QTVERSION < '4.0.0':
        a.setMainWidget(w)
    w.show()
    if QTVERSION < '4.0.0':
        a.exec_loop()
    else:
        a.exec_()
if __name__ == "__main__":
    testwidget()
