###############################################################################
#                                                                             #
# The MIT License                                                             #
#                                                                             #
# Copyright (C) 2017 by Juergen Skrotzky (JorgenVikingGod@gmail.com)          #
#               >> https://github.com/Jorgen-VikingGod                        #
#                                                                             #
# Sources: https://github.com/Jorgen-VikingGod/Qt-Frameless-Window-DarkStyle  #
#                                                                             #
###############################################################################
"""DarkStyle color palette."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QStyleFactory

STYLESHEET = """
QToolTip{
  color:#ffffff;
  background-color:palette(base);
  border:1px solid palette(highlight);
  border-radius:4px;
}
QStatusBar{
  background-color:rgba(25,25,25,127);
  color:palette(mid);
}
QMenuBar{
  background-color:rgba(32,32,32,127);
  border-bottom:2px solid rgba(25,25,25,75);
}
QMenuBar::item{
  spacing:2px;
  padding:3px 4px;
  background:transparent;
}
QMenuBar::item:selected{
  background-color:rgba(106,106,106,255);
  border-left:1px solid rgba(106,106,106,127);
  border-right:1px solid rgba(106,106,106,127);
}
QMenuBar::item:pressed{
  background-color:palette(highlight);
  border-left:1px solid rgba(25,25,25,127);
  border-right:1px solid rgba(25,25,25,127);
}
QMenu{
  background-color:palette(window);
  border:1px solid palette(shadow);
}
QMenu::item{
  padding:3px 25px 3px 20px;
  border:1px solid transparent;
}
QMenu::item:disabled{
  background-color:rgba(35,35,35,127);
  color:palette(disabled);
}
QMenu::item:selected{
  border-color:rgba(147,191,236,127);
  background:palette(highlight);
}
QMenu::icon{
  padding-left:20px;
}
QMenu::icon:checked{
  background-color:rgba(25,25,25,127);
  border:1px solid palette(highlight);
  border-radius:2px;
}
QMenu::separator{
  height:1px;
  background:palette(alternate-base);
  margin-left:5px;
  margin-right:5px;
}
QMenu::indicator{
  width:18px;
  height:18px;
}
QToolBar::top{
  background-color:rgba(25,25,25,127);
  border-bottom:3px solid rgba(25,25,25,127);
}
QToolBar::bottom{
  background-color:rgba(25,25,25,127);
  border-top:3px solid rgba(25,25,25,127);
}
QToolBar::left{
  background-color:rgba(25,25,25,127);
  border-right:3px solid rgba(25,25,25,127);
}
QToolBar::right{
  background-color:rgba(25,25,25,127);
  border-left:3px solid rgba(25,25,25,127);
}
QMainWindow::separator{
  width:6px;
  height:5px;
  padding:2px;
}
QSplitter::handle:horizontal{
  width:10px;
}
QSplitter::handle:vertical{
  height:10px;
}
QDockWidget::title{
  padding:4px;
  background-color:rgba(25,25,25,127);
  border:1px solid rgba(25,25,25,75);
  border-bottom:2px solid rgba(25,25,25,75);
}
QDockWidget::close-button,QDockWidget::float-button{
  subcontrol-position:top right;
  subcontrol-origin:margin;
  position:absolute;
  top:3px;
  bottom:0px;
  width:20px;
  height:20px;
}
QDockWidget::close-button{
  right:3px;
}
QDockWidget::float-button{
  right:25px;
}
QGroupBox{
  background-color:rgba(66,66,66,50%);
  border:1px solid rgba(25,25,25,127);
  border-radius:4px;
}
QGroupBox::title{
  subcontrol-origin:margin;
  subcontrol-position:left top;
  padding:4px 6px;
  margin-left:3px;
  background-color:rgba(25,25,25,127);
  border:1px solid rgba(25,25,25,75);
  border-bottom:2px solid rgb(127,127,127);
  border-top-left-radius:4px;
  border-top-right-radius:4px;
}
QTabWidget::pane{
  background-color:rgba(66,66,66,50%);
  border-top:1px solid rgba(25,25,25,50%);
}
QTabWidget::tab-bar{
  left:3px;
  top:1px;
}
QTabBar{
  background-color:transparent;
  qproperty-drawBase:0;
  border-bottom:1px solid rgba(25,25,25,50%);
}
QTabBar::tab{
  height: 20px;
  width: 75px;
  background-color: rgba(25,25,25,127);
  border:1px solid rgba(25,25,25,75);
  border-top-left-radius:4px;
  border-top-right-radius:4px;
}
QTabBar::tab:selected,QTabBar::tab:hover{
  background-color:rgba(53,53,53,127);
  border-bottom-color:rgba(66,66,66,75%);
}
QTabBar::tab:selected{
  border-bottom:2px solid palette(highlight);
}
QTabBar::tab::selected:disabled{
  border-bottom:2px solid rgb(127,127,127);
}
QTabBar::tab:!selected{
  margin-top:2px;
}
QTreeView::item{
  margin: 5px;
}

QTreeView, QTableView{
  alternate-background-color: rgb(23,23,23);
  background:palette(base);
  border-radius: 5px;
}
QTreeView QHeaderView::section, QTableView QHeaderView::section{
  background-color: rgba(32,32,32,255);
  border-style:none;
  border-bottom:1px solid palette(dark);
  border-right:1px solid palette(dark);
  border-left:1px solid palette(base);
  padding:2px;
  border-radius: 5px;
}

/* COMBO BOX A VALIDER
QComboBox, QComboBox::drop-down:editable{
  background-color: rgba(32,32,32,255);
  border-style:none;
  padding:2px;
  border-radius: 5px;
}
QComboBox::down-arrow {
    image:url(:/icons/combo_closed.png);
}
QComboBox::down-arrow:on {
  image:url(:/icons/icon_branch_open.png);
}
QComboBox:!editable:on, QComboBox::drop-down:editable:on {
  background-color: rgba(40,40,40,255);
}
*/

QMenu{
    border-style: none;
    padding: 2px;
}
QMenu::item{
    border-radius: 2px;
}
QMenuBar{
    border-style: none;
    padding: 2px;
}
QMenuBar::item{
    padding: 5px;
    border-radius: 2px;
}
QHeaderView{
  background-color: rgba(0,0,0,0);
}
QTreeView::item:selected:disabled, QTableView::item:selected:disabled{
  background:rgb(80,80,80);
}

QTreeView::item:selected{
}
QTreeView::branch{
  background-color:palette(base);
}

QTreeView::branch:has-siblings:!adjoins-item{
  border-image:url(:/icons/icon_vline.png) 0;
}
QTreeView::branch:has-siblings:adjoins-item{
  border-image:url(:/icons/icon_branch_more.png) 0;
}
QTreeView::branch:!has-children:!has-siblings:adjoins-item{
  border-image:url(:/icons/icon_branch_end.png) 0;
}
QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings{
  border-image:none;
  image:url(:/icons/icon_branch_closed.png);
}
QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings{
  border-image:none;
  image:url(:/icons/icon_branch_open.png);
}
QScrollBar:vertical{
  background:palette(base);
  border-top-right-radius:2px;
  border-bottom-right-radius:2px;
  width:16px;
  margin:0px;
}
QScrollBar::handle:vertical{
  background-color:palette(alternate-base);
  border-radius:2px;
  min-height:20px;
  margin:2px 4px 2px 4px;
}
QScrollBar::handle:vertical:hover{
  background-color:palette(highlight);
}
QScrollBar::add-line:vertical{
  background:none;
  height:0px;
  subcontrol-position:right;
  subcontrol-origin:margin;
}

QScrollArea { background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollArea > QWidget > QScrollBar { background: palette(base); }

QScrollBar::sub-line:vertical{
  background:none;
  height:0px;
  subcontrol-position:left;
  subcontrol-origin:margin;
}
QScrollBar:horizontal{
  background:palette(base);
  height:16px;
  margin:0px;
}
QScrollBar::handle:horizontal{
  background-color:palette(alternate-base);
  border-radius:2px;
  min-width:20px;
  margin:4px 2px 4px 2px;
}
QScrollBar::handle:horizontal:hover{
  background-color:palette(highlight);
}
QScrollBar::add-line:horizontal{
  background:none;
  width:0px;
  subcontrol-position:bottom;
  subcontrol-origin:margin;
}
QScrollBar::sub-line:horizontal{
  background:none;
  width:0px;
  subcontrol-position:top;
  subcontrol-origin:margin;
}
QSlider::handle:horizontal{
  border-radius:4px;
  border:1px solid rgba(25,25,25,255);
  background-color:palette(alternate-base);
  min-height:20px;
  margin:0 -4px;
}
QSlider::handle:horizontal:hover{
  background:palette(highlight);
}
QSlider::add-page:horizontal{
  background:palette(base);
}
QSlider::sub-page:horizontal{
  background:palette(highlight);
}
QSlider::sub-page:horizontal:disabled{
  background:rgb(80,80,80);
}

"""


def _dark(palette):
    # modify palette to dark
    palette.setColor(QPalette.Window, QColor(53, 53, 58))
    palette.setColor(QPalette.WindowText, QColor(200, 200, 200))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    palette.setColor(QPalette.Base, QColor(46, 50, 58))
    palette.setColor(QPalette.AlternateBase, QColor(60, 65, 70))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, QColor(53, 53, 58))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.Dark, QColor(35, 35, 35))
    palette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    palette.setColor(QPalette.Button, QColor(53, 53, 58))
    palette.setColor(QPalette.ButtonText, QColor(200, 200, 200))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(80, 80, 80))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(127, 127, 127))
    return palette


def _material(palette):
    # modify palette to material
    palette.setColor(QPalette.Window, QColor(18, 18, 18))
    palette.setColor(QPalette.WindowText, QColor(186, 186, 186))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    palette.setColor(QPalette.Base, QColor(27, 27, 27))
    palette.setColor(QPalette.AlternateBase, QColor(18, 18, 18))
    palette.setColor(QPalette.ToolTipBase, QColor(0, 255, 0))
    palette.setColor(QPalette.ToolTipText, QColor(0, 255, 0))
    palette.setColor(QPalette.Text, QColor(227, 227, 227))
    palette.setColor(QPalette.PlaceholderText, QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.Dark, QColor(27, 27, 27))
    palette.setColor(QPalette.Shadow, QColor(27, 27, 27))
    palette.setColor(QPalette.Button, QColor(18, 18, 18))
    palette.setColor(QPalette.ButtonText, QColor(186, 186, 186))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    palette.setColor(QPalette.BrightText, QColor(0, 255, 0))
    palette.setColor(QPalette.Link, QColor(85, 136, 255))
    palette.setColor(QPalette.Highlight, QColor(85, 136, 255))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(127, 127, 127))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(127, 127, 127))
    return palette


def apply(app):
    """Apply the stylesheet."""
    # set app style
    app.setStyle(QStyleFactory.create("fusion"))
    # polish palette
    app.setPalette(_material(app.palette()))
    # set stylesheet
    app.setStyleSheet(STYLESHEET)
