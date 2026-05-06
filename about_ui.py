from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap
import common as cmn
from objects import kProgramName

class AboutDialog(cmn.Dialog):
    version = '1.1'
    about_text = '''<b>%s - An expert system shell</b><br/>Version %s
<br/>
Copyright © 2018 Damir Akhmetzyanov (linesprower@gmail.com) 
<br/>
<br/>
Funduck ESS is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
<br/>
<br/>
This program uses icons from the 
<a href="http://p.yusukekamiyamane.com/index.html.en">Fugue Icons</a>
set by Yusuke Kamiyamane licensed under <a href="https://creativecommons.org/licenses/by/3.0/">CC BY 3.0</a>
<br/>
<br/>
The "Duckling" logo by <a href="https://smashicons.com/">SmashIcons</a> 
from <a href="www.flaticon.com">www.flaticon.com</a> 
''' % (kProgramName, version)

    def __init__(self):
        cmn.Dialog.__init__(self, 'ESS', 'AboutBox', 'About %s' % kProgramName)
        self.setWindowIcon(cmn.GetIcon('icons/info.png'))
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(QPixmap('icons/duckling.png'))
        
        lbl = QLabel(self.about_text)
        lbl.setWordWrap(True)
        lbl.setOpenExternalLinks(True)
        
        icon_box = cmn.VBox([icon_lbl], align=cmn.kTopAlign)
        layout = cmn.HBox([icon_box, lbl], 15, 15)
        
        self.setDialogLayout(layout, lambda: None, has_statusbar=False, close_btn=True, 
                             extra_buttons=[('View license text', self.showLicense)])
        
    def showLicense(self):
        try:
            with open('LICENSE.txt', encoding='utf-8') as f:
                text = f.read()
            cmn.showReport('License Agreement', text)
        except FileNotFoundError:
            cmn.showReport('License Agreement', 'File not found.')