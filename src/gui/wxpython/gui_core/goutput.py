"""
@package gui_core.goutput

@brief Command output widgets

Classes:
 - goutput::GConsoleWindow
 - goutput::GStc
 - goutput::GConsoleFrame

(C) 2007-2012 by the GRASS Development Team

This program is free software under the GNU General Public License
(>=v2). Read the file COPYING that comes with GRASS for details.

@author Michael Barton (Arizona State University)
@author Martin Landa <landa.martin gmail.com>
@author Vaclav Petras <wenzeslaus gmail.com>  (refactoring)
@author Anna Kratochvilova <kratochanna gmail.com> (refactoring)
"""

import os
import textwrap

import wx
from   wx import stc

from grass.pydispatch.signal import Signal

from core.gcmd       import GError, EncodeString
from core.gconsole   import GConsole, \
    EVT_CMD_OUTPUT, EVT_CMD_PROGRESS, EVT_CMD_RUN, EVT_CMD_DONE, \
    Notification
from gui_core.prompt import GPromptSTC
from core.settings   import UserSettings
from core.utils import _
from gui_core.widgets import SearchModuleWidget


GC_EMPTY = 0
GC_SEARCH = 1
GC_PROMPT = 2


class GConsoleWindow(wx.SplitterWindow):
    """Create and manage output console for commands run by GUI.
    """
    def __init__(self, parent, gconsole, menuModel = None, margin = False,
                 style = wx.TAB_TRAVERSAL | wx.FULL_REPAINT_ON_RESIZE,
                 gcstyle = GC_EMPTY,
                 **kwargs):
        """
        :param parent: gui parent
        :param gconsole: console logic
        :param menuModel: tree model of modules (from menu)
        :param margin: use margin in output pane (GStc)
        :param style: wx.SplitterWindow style
        :param gcstyle: GConsole style
                        (GC_EMPTY, GC_PROMPT to show command prompt,
                        GC_SEARCH to show search widget)
        """
        wx.SplitterWindow.__init__(self, parent, id = wx.ID_ANY, style = style, **kwargs)
        self.SetName("GConsole")
        
        self.panelOutput = wx.Panel(parent=self, id=wx.ID_ANY)
        self.panelProgress = wx.Panel(parent=self.panelOutput, id=wx.ID_ANY, name='progressPanel')
        self.panelPrompt = wx.Panel(parent=self, id=wx.ID_ANY)
        # initialize variables
        self.parent = parent # GMFrame | CmdPanel | ?
        self._gconsole = gconsole
        self._menuModel = menuModel

        self._gcstyle = gcstyle
        self.lineWidth       = 80

        # signal which requests showing of a notification
        self.showNotification = Signal("GConsoleWindow.showNotification")
        # signal emitted when text appears in the console
        # parameter 'notification' suggests form of notification (according to
        # core.giface.Notification)
        self.contentChanged = Signal("GConsoleWindow.contentChanged")

        # progress bar
        self.progressbar = wx.Gauge(parent = self.panelProgress, id = wx.ID_ANY,
                                    range = 100, pos = (110, 50), size = (-1, 25),
                                    style = wx.GA_HORIZONTAL)
        self._gconsole.Bind(EVT_CMD_PROGRESS, self.OnCmdProgress)
        self._gconsole.Bind(EVT_CMD_OUTPUT, self.OnCmdOutput)
        self._gconsole.Bind(EVT_CMD_RUN, self.OnCmdRun)
        self._gconsole.Bind(EVT_CMD_DONE, self.OnCmdDone)

        self._gconsole.writeLog.connect(self.WriteLog)
        self._gconsole.writeCmdLog.connect(self.WriteCmdLog)
        self._gconsole.writeWarning.connect(self.WriteWarning)
        self._gconsole.writeError.connect(self.WriteError)

        # text control for command output
        self.cmdOutput = GStc(parent = self.panelOutput, id = wx.ID_ANY, margin = margin,
                               wrap = None)

        # search & command prompt
        # move to the if below
        # search depends on cmd prompt
        self.cmdPrompt = GPromptSTC(parent=self, menuModel=self._menuModel)
        self.cmdPrompt.promptRunCmd.connect(lambda cmd:
                                            self._gconsole.RunCmd(command=cmd))
        self.cmdPrompt.showNotification.connect(self.showNotification)

        if not self._gcstyle & GC_PROMPT:
            self.cmdPrompt.Hide()


        if self._gcstyle & GC_SEARCH:
            self.infoCollapseLabelExp = _("Click here to show search module engine")
            self.infoCollapseLabelCol = _("Click here to hide search module engine")
            self.searchPane = wx.CollapsiblePane(parent = self.panelOutput,
                                                 label = self.infoCollapseLabelExp,
                                                 style = wx.CP_DEFAULT_STYLE |
                                                 wx.CP_NO_TLW_RESIZE | wx.EXPAND)
            self.MakeSearchPaneContent(self.searchPane.GetPane(), self._menuModel)
            self.searchPane.Collapse(True)
            self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.OnSearchPaneChanged, self.searchPane) 
            self.search.moduleSelected.connect(lambda name:
                                               self.cmdPrompt.SetTextAndFocus(name + ' '))
        else:
            self.search = None


        if self._gcstyle & GC_PROMPT:
            cmdLabel = _("Command prompt")
            self.outputBox = wx.StaticBox(parent = self.panelOutput, id = wx.ID_ANY,
                                          label = " %s " % _("Output window"))

            self.cmdBox = wx.StaticBox(parent = self.panelOutput, id = wx.ID_ANY,
                                       label = " %s " % cmdLabel)

        # buttons
        self.btnOutputClear = wx.Button(parent = self.panelOutput, id = wx.ID_CLEAR)
        self.btnOutputClear.SetToolTipString(_("Clear output window content"))
        self.btnCmdClear = wx.Button(parent = self.panelOutput, id = wx.ID_CLEAR)
        self.btnCmdClear.SetToolTipString(_("Clear command prompt content"))
        self.btnOutputSave  = wx.Button(parent = self.panelOutput, id = wx.ID_SAVE)
        self.btnOutputSave.SetToolTipString(_("Save output window content to the file"))
        self.btnCmdAbort = wx.Button(parent = self.panelProgress, id = wx.ID_STOP)
        self.btnCmdAbort.SetToolTipString(_("Abort running command"))
        self.btnCmdProtocol = wx.ToggleButton(parent = self.panelOutput, id = wx.ID_ANY,
                                              label = _("&Log file"),
                                              size = self.btnCmdClear.GetSize())
        self.btnCmdProtocol.SetToolTipString(_("Toggle to save list of executed commands into "
                                               "a file; content saved when switching off."))
        
        if not self._gcstyle & GC_PROMPT:
            self.btnCmdClear.Hide()
            self.btnCmdProtocol.Hide()
        
        self.btnCmdClear.Bind(wx.EVT_BUTTON,     self.cmdPrompt.OnCmdErase)
        self.btnOutputClear.Bind(wx.EVT_BUTTON,  self.OnOutputClear)
        self.btnOutputSave.Bind(wx.EVT_BUTTON,   self.OnOutputSave)
        self.btnCmdAbort.Bind(wx.EVT_BUTTON,     self._gconsole.OnCmdAbort)
        self.btnCmdProtocol.Bind(wx.EVT_TOGGLEBUTTON, self.OnCmdProtocol)
        
        self._layout()
        
    def _layout(self):
        """Do layout"""
        self.outputSizer = wx.BoxSizer(wx.VERTICAL)
        progressSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        if self._gcstyle & GC_PROMPT:
            outBtnSizer = wx.StaticBoxSizer(self.outputBox, wx.HORIZONTAL)
            cmdBtnSizer = wx.StaticBoxSizer(self.cmdBox, wx.HORIZONTAL)
        else:
            outBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
            cmdBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
            
        
        if self._gcstyle & GC_PROMPT:
            promptSizer = wx.BoxSizer(wx.VERTICAL)
            promptSizer.Add(item = self.cmdPrompt, proportion = 1,
                        flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border = 3)
            helpText = wx.StaticText(self.panelPrompt, id = wx.ID_ANY,
                                 label = "Press Tab to display command help, Ctrl+Space to autocomplete")
            helpText.SetForegroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_GRAYTEXT))
            promptSizer.Add(item = helpText,
                            proportion = 0, flag = wx.EXPAND | wx.LEFT, border = 5)
        
        if self._gcstyle & GC_SEARCH:
            self.outputSizer.Add(item = self.searchPane, proportion = 0,
                            flag = wx.EXPAND | wx.ALL, border = 3)
        self.outputSizer.Add(item = self.cmdOutput, proportion = 1,
                        flag = wx.EXPAND | wx.ALL, border = 3)
        if self._gcstyle & GC_PROMPT:
            proportion = 1
        else:
            proportion = 0
            outBtnSizer.AddStretchSpacer()

        outBtnSizer.Add(item = self.btnOutputClear, proportion = proportion,
                        flag = wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, border = 5)

        outBtnSizer.Add(item = self.btnOutputSave, proportion = proportion,
                        flag = wx.ALIGN_RIGHT | wx.RIGHT, border = 5)

        cmdBtnSizer.Add(item = self.btnCmdProtocol, proportion = 1,
                        flag = wx.ALIGN_CENTER | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, border = 5)
        cmdBtnSizer.Add(item = self.btnCmdClear, proportion = 1,
                        flag = wx.ALIGN_CENTER | wx.RIGHT, border = 5)
        progressSizer.Add(item = self.btnCmdAbort, proportion = 0,
                          flag = wx.ALL|wx.ALIGN_CENTER, border = 5)
        progressSizer.Add(item = self.progressbar, proportion = 1,
                          flag = wx.ALIGN_CENTER|wx.RIGHT|wx.TOP|wx.BOTTOM, border = 5)
                          
        self.panelProgress.SetSizer(progressSizer)
        progressSizer.Fit(self.panelProgress)
        
        btnSizer.Add(item = outBtnSizer, proportion = 1,
                     flag = wx.ALL | wx.ALIGN_CENTER, border = 5)
        btnSizer.Add(item = cmdBtnSizer, proportion = 1,
                     flag = wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM | wx.RIGHT, border = 5)
        self.outputSizer.Add(item = self.panelProgress, proportion = 0,
                        flag = wx.EXPAND)
        self.outputSizer.Add(item = btnSizer, proportion = 0,
                        flag = wx.EXPAND)
        
        self.outputSizer.Fit(self)
        self.outputSizer.SetSizeHints(self)
        self.panelOutput.SetSizer(self.outputSizer)
        # eliminate gtk_widget_size_allocate() warnings
        # avoid to use a deprecated method in wxPython >= 2.9
        getattr(self.outputSizer, 'FitInside',
                self.outputSizer.SetVirtualSizeHints)(self.panelOutput)
        
        if self._gcstyle & GC_PROMPT:
            promptSizer.Fit(self)
            promptSizer.SetSizeHints(self)
            self.panelPrompt.SetSizer(promptSizer)
        
        # split window
        if self._gcstyle & GC_PROMPT:
            self.SplitHorizontally(self.panelOutput, self.panelPrompt, -50)
        else:
            self.SplitHorizontally(self.panelOutput, self.panelPrompt, -45)
            self.Unsplit()
        self.SetMinimumPaneSize(self.btnCmdClear.GetSize()[1] + 25)
        
        self.SetSashGravity(1.0)
        
        self.outputSizer.Hide(self.panelProgress)
        # layout
        self.SetAutoLayout(True)
        self.Layout()

    def MakeSearchPaneContent(self, pane, model):
        """Create search pane"""
        border = wx.BoxSizer(wx.VERTICAL)
        
        self.search = SearchModuleWidget(parent = pane,
                                         model = model)

        self.search.showNotification.connect(self.showNotification)

        border.Add(item = self.search, proportion = 0,
                   flag = wx.EXPAND | wx.ALL, border = 1)
        
        pane.SetSizer(border)
        border.Fit(pane)
        
    def OnSearchPaneChanged(self, event):
        """Collapse search module box"""
        if self.searchPane.IsExpanded():
            self.searchPane.SetLabel(self.infoCollapseLabelCol)
        else:
            self.searchPane.SetLabel(self.infoCollapseLabelExp)
        
        self.panelOutput.Layout()
        self.panelOutput.SendSizeEvent()
        
    def GetPanel(self, prompt = True):
        """Get panel

        :param prompt: get prompt / output panel

        :return: wx.Panel reference
        """
        if prompt:
            return self.panelPrompt

        return self.panelOutput

    def WriteLog(self, text, style=None, wrap=None,
                 notification=Notification.HIGHLIGHT):
        """Generic method for writing log message in 
        given style. 

        Emits contentChanged signal.

        :param line: text line
        :param style: text style (see GStc)
        :param stdout: write to stdout or stderr
        :param notification: form of notification
        """

        self.cmdOutput.SetStyle()

        # documenting old behavior/implementation:
        # switch notebook if required
        # now, let user to bind to the old event

        if not style:
            style = self.cmdOutput.StyleDefault
        
        # p1 = self.cmdOutput.GetCurrentPos()
        p1 = self.cmdOutput.GetEndStyled()
        # self.cmdOutput.GotoPos(p1)
        self.cmdOutput.DocumentEnd()
        
        for line in text.splitlines():
            # fill space
            if len(line) < self.lineWidth:
                diff = self.lineWidth - len(line) 
                line += diff * ' '
            
            self.cmdOutput.AddTextWrapped(line, wrap = wrap) # adds '\n'
            
            p2 = self.cmdOutput.GetCurrentPos()
            
            self.cmdOutput.StartStyling(p1, 0xff)
            self.cmdOutput.SetStyling(p2 - p1, style)
        
        self.cmdOutput.EnsureCaretVisible()

        self.contentChanged.emit(notification=notification)
        
    def WriteCmdLog(self, text, pid=None, notification=Notification.MAKE_VISIBLE):
        """Write message in selected style
        
        :param text: message to be printed
        :param pid: process pid or None
        :param switchPage: True to switch page
        """
        if pid:
            text = '(' + str(pid) + ') ' + text
        self.WriteLog(text, style=self.cmdOutput.StyleCommand, notification=notification)

    def WriteWarning(self, text):
        """Write message in warning style"""
        self.WriteLog(text, style=self.cmdOutput.StyleWarning, notification=Notification.MAKE_VISIBLE)

    def WriteError(self, text):
        """Write message in error style"""
        self.WriteLog(text, style=self.cmdOutput.StyleError, notification=Notification.MAKE_VISIBLE)

    def OnOutputClear(self, event):
        """Clear content of output window"""
        self.cmdOutput.SetReadOnly(False)
        self.cmdOutput.ClearAll()
        self.cmdOutput.SetReadOnly(True)
        self.progressbar.SetValue(0)

    def GetProgressBar(self):
        """Return progress bar widget"""
        return self.progressbar

    def OnOutputSave(self, event):
        """Save (selected) text from output window to the file"""
        text = self.cmdOutput.GetSelectedText()
        if not text:
            text = self.cmdOutput.GetText()
        
        # add newline if needed
        if len(text) > 0 and text[-1] != '\n':
            text += '\n'
        
        dlg = wx.FileDialog(self, message = _("Save file as..."),
                            defaultFile = "grass_cmd_output.txt",
                            wildcard = _("%(txt)s (*.txt)|*.txt|%(files)s (*)|*") % 
                            {'txt': _("Text files"), 'files': _("Files")},
                            style = wx.SAVE | wx.FD_OVERWRITE_PROMPT)
        
        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            
            try:
                output = open(path, "w")
                output.write(text)
            except IOError as e:
                GError(_("Unable to write file '%(path)s'.\n\nDetails: %(error)s") % {'path': path, 'error': e})
            finally:
                output.close()
            message = _("Command output saved into '%s'") % path
            self.showNotification.emit(message = message)
        
        dlg.Destroy()

    def SetCopyingOfSelectedText(self, copy):
        """Enable or disable copying of selected text in to clipboard.
        Effects prompt and output.
        
        :param bool copy: True for enable, False for disable
        """
        if copy:
            self.cmdPrompt.Bind(stc.EVT_STC_PAINTED, self.cmdPrompt.OnTextSelectionChanged)
            self.cmdOutput.Bind(stc.EVT_STC_PAINTED, self.cmdOutput.OnTextSelectionChanged)
        else:
            self.cmdPrompt.Unbind(stc.EVT_STC_PAINTED)
            self.cmdOutput.Unbind(stc.EVT_STC_PAINTED)

    def OnCmdOutput(self, event):
        """Prints command output.

        Emits contentChanged signal.
        """
        message = event.text
        type  = event.type

        self.cmdOutput.AddStyledMessage(message, type)

        if event.type in ('warning', 'error'):
            self.contentChanged.emit(notification=Notification.MAKE_VISIBLE)
        else:
            self.contentChanged.emit(notification=Notification.HIGHLIGHT)

    def OnCmdProgress(self, event):
        """Update progress message info"""
        self.progressbar.SetValue(event.value)
        event.Skip()

    def CmdProtocolSave(self):
        """Save list of manually entered commands into a text log file"""
        if not hasattr(self, 'cmdFileProtocol'):
            return # it should not happen
        
        try:
            output = open(self.cmdFileProtocol, "a")
            cmds = self.cmdPrompt.GetCommands()
            output.write('\n'.join(cmds))
            if len(cmds) > 0:
                output.write('\n')
        except IOError as e:
            GError(_("Unable to write file '%(filePath)s'.\n\nDetails: %(error)s") % 
                    {'filePath': self.cmdFileProtocol, 'error': e})
        finally:
            output.close()
        
        message = _("Command log saved to '%s'") % self.cmdFileProtocol
        self.showNotification.emit(message = message)
        del self.cmdFileProtocol
        
    def OnCmdProtocol(self, event = None):
        """Save commands into file"""
        if not event.IsChecked():
            # stop capturing commands, save list of commands to the
            # protocol file
            self.CmdProtocolSave()
        else:
            # start capturing commands
            self.cmdPrompt.ClearCommands()
            # ask for the file
            dlg = wx.FileDialog(self, message = _("Save file as..."),
                                defaultFile = "grass_cmd_log.txt",
                                wildcard = _("%(txt)s (*.txt)|*.txt|%(files)s (*)|*") % 
                                            {'txt': _("Text files"), 'files': _("Files")},
                                style = wx.SAVE)
            if dlg.ShowModal() == wx.ID_OK:
                self.cmdFileProtocol = dlg.GetPath()
            else:
                wx.CallAfter(self.btnCmdProtocol.SetValue, False)
            
            dlg.Destroy()
            
        event.Skip()

    def OnCmdRun(self, event):
        """Run command"""
        self.outputSizer.Show(self.panelProgress)
        self.outputSizer.Layout()
        event.Skip()

    def OnCmdDone(self, event):
        """Command done (or aborted)
        """
        self.progressbar.SetValue(0) # reset progress bar on '0%'
        wx.CallLater(100, self._hideProgress)
        event.Skip()

    def _hideProgress(self):
        self.outputSizer.Hide(self.panelProgress)
        self.outputSizer.Layout()

    def ResetFocus(self):
        """Reset focus"""
        self.cmdPrompt.SetFocus()
        
    def GetPrompt(self):
        """Get prompt"""
        return self.cmdPrompt


class GStc(stc.StyledTextCtrl):
    """Styled text control for GRASS stdout and stderr.

    Based on FrameOutErr.py

    Name:      FrameOutErr.py
    Purpose:   Redirecting stdout / stderr
    Author:    Jean-Michel Fauth, Switzerland
    Copyright: (c) 2005-2007 Jean-Michel Fauth
    Licence:   GPL
    """  
    def __init__(self, parent, id, margin = False, wrap = None):
        stc.StyledTextCtrl.__init__(self, parent, id)
        self.parent = parent
        self.SetUndoCollection(True)
        self.SetReadOnly(True)

        # remember position of line begining (used for '\r')
        self.linePos         = -1

        #
        # styles
        #                
        self.SetStyle()
        
        #
        # line margins
        #
        # TODO print number only from cmdlog
        self.SetMarginWidth(1, 0)
        self.SetMarginWidth(2, 0)
        if margin:
            self.SetMarginType(0, stc.STC_MARGIN_NUMBER)
            self.SetMarginWidth(0, 30)
        else:
            self.SetMarginWidth(0, 0)

        #
        # miscellaneous
        #
        self.SetViewWhiteSpace(False)
        self.SetTabWidth(4)
        self.SetUseTabs(False)
        self.UsePopUp(True)
        self.SetSelBackground(True, "#FFFF00")
        self.SetUseHorizontalScrollBar(True)

        #
        # bindings
        #
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        
    def OnTextSelectionChanged(self, event):
        """Copy selected text to clipboard and skip event.
        The same function is in TextCtrlAutoComplete class (prompt.py).
        """
        wx.CallAfter(self.Copy)
        event.Skip()
        
    def SetStyle(self):
        """Set styles for styled text output windows with type face 
        and point size selected by user (Courier New 10 is default)"""
        
        typeface = UserSettings.Get(group = 'appearance', key = 'outputfont', subkey = 'type')   
        if typeface == "":
            typeface = "Courier New"
        
        typesize = UserSettings.Get(group = 'appearance', key = 'outputfont', subkey = 'size')
        if typesize == None or typesize <= 0:
            typesize = 10
        typesize = float(typesize)
        
        self.StyleDefault     = 0
        self.StyleDefaultSpec = "face:%s,size:%d,fore:#000000,back:#FFFFFF" % (typeface, typesize)
        self.StyleCommand     = 1
        self.StyleCommandSpec = "face:%s,size:%d,,fore:#000000,back:#bcbcbc" % (typeface, typesize)
        self.StyleOutput      = 2
        self.StyleOutputSpec  = "face:%s,size:%d,,fore:#000000,back:#FFFFFF" % (typeface, typesize)
        # fatal error
        self.StyleError       = 3
        self.StyleErrorSpec   = "face:%s,size:%d,,fore:#7F0000,back:#FFFFFF" % (typeface, typesize)
        # warning
        self.StyleWarning     = 4
        self.StyleWarningSpec = "face:%s,size:%d,,fore:#0000FF,back:#FFFFFF" % (typeface, typesize)
        # message
        self.StyleMessage     = 5
        self.StyleMessageSpec = "face:%s,size:%d,,fore:#000000,back:#FFFFFF" % (typeface, typesize)
        # unknown
        self.StyleUnknown     = 6
        self.StyleUnknownSpec = "face:%s,size:%d,,fore:#000000,back:#FFFFFF" % (typeface, typesize)
        
        # default and clear => init
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, self.StyleDefaultSpec)
        self.StyleClearAll()
        self.StyleSetSpec(self.StyleCommand, self.StyleCommandSpec)
        self.StyleSetSpec(self.StyleOutput,  self.StyleOutputSpec)
        self.StyleSetSpec(self.StyleError,   self.StyleErrorSpec)
        self.StyleSetSpec(self.StyleWarning, self.StyleWarningSpec)
        self.StyleSetSpec(self.StyleMessage, self.StyleMessageSpec)
        self.StyleSetSpec(self.StyleUnknown, self.StyleUnknownSpec)        

    def OnDestroy(self, evt):
        """The clipboard contents can be preserved after
        the app has exited"""
        
        wx.TheClipboard.Flush()
        evt.Skip()

    def AddTextWrapped(self, txt, wrap = None):
        """Add string to text area.

        String is wrapped and linesep is also added to the end
        of the string"""
        # allow writing to output window
        self.SetReadOnly(False)

        if wrap:
            txt = textwrap.fill(txt, wrap) + '\n'
        else:
            if txt[-1] != '\n':
                txt += '\n'

        if '\r' in txt:
            self.linePos = -1
            for seg in txt.split('\r'):
                if self.linePos > -1:
                    self.SetCurrentPos(self.linePos)
                    self.ReplaceSelection(seg)
                else:
                    self.linePos = self.GetCurrentPos()
                    self.AddText(seg)
        else:
            self.linePos = self.GetCurrentPos()
            
            try:
                self.AddText(txt)
            except UnicodeDecodeError:
                enc = UserSettings.Get(group = 'atm', key = 'encoding', subkey = 'value')
                if enc:
                    txt = unicode(txt, enc, errors = 'replace')
                elif 'GRASS_DB_ENCODING' in os.environ:
                    txt = unicode(txt, os.environ['GRASS_DB_ENCODING'], errors = 'replace')
                else:
                    txt = EncodeString(txt)
                
                self.AddText(txt)

        # reset output window to read only
        self.SetReadOnly(True)

    def AddStyledMessage(self, message, style = None):
        """Add message to text area.

        Handles messages with progress percentages.

        :param message: message to be added
        :param style: style of message, allowed values: 'message',
                      'warning', 'error' or None
        """
        # message prefix
        if style == 'warning':
            message = 'WARNING: ' + message
        elif style == 'error':
            message = 'ERROR: ' + message
        
        p1 = self.GetEndStyled()
        self.GotoPos(p1)
        
        # is this still needed?
        if '\b' in message:
            if self.linePos < 0:
                self.linePos = p1
            last_c = ''
            for c in message:
                if c == '\b':
                    self.linePos -= 1
                else:
                    if c == '\r':
                        pos = self.GetCurLine()[1]
                        # self.SetCurrentPos(pos)
                    else:
                        self.SetCurrentPos(self.linePos)
                    self.ReplaceSelection(c)
                    self.linePos = self.GetCurrentPos()
                    if c != ' ':
                        last_c = c
            if last_c not in ('0123456789'):
                self.AddTextWrapped('\n', wrap = None)
                self.linePos = -1
        else:
            self.linePos = -1 # don't force position
            if '\n' not in message:
                self.AddTextWrapped(message, wrap = 60)
            else:
                self.AddTextWrapped(message, wrap = None)
        p2 = self.GetCurrentPos()
        
        if p2 >= p1:
            self.StartStyling(p1, 0xff)
        
            if style == 'error':
                self.SetStyling(p2 - p1, self.StyleError)
            elif style == 'warning':
                self.SetStyling(p2 - p1, self.StyleWarning)
            elif style == 'message':
                self.SetStyling(p2 - p1, self.StyleMessage)
            else: # unknown
                self.SetStyling(p2 - p1, self.StyleUnknown)
        
        self.EnsureCaretVisible()


class GConsoleFrame(wx.Frame):
    """Standalone GConsole for testing only"""
    def __init__(self, parent, id = wx.ID_ANY, title = "GConsole Test Frame",
                 style = wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL, **kwargs):
        wx.Frame.__init__(self, parent = parent, id = id, title = title, style = style)

        panel = wx.Panel(self, id = wx.ID_ANY)
        
        from lmgr.menudata import LayerManagerMenuData
        menuTreeBuilder = LayerManagerMenuData()
        self.gconsole = GConsole(guiparent=self)
        self.goutput = GConsoleWindow(parent = panel, gconsole = self.gconsole,
                                      menuModel=menuTreeBuilder.GetModel(),
                                      gcstyle = GC_SEARCH | GC_PROMPT)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(item = self.goutput, proportion = 1, flag = wx.EXPAND, border = 0)

        panel.SetSizer(mainSizer)
        mainSizer.Fit(panel)
        self.SetMinSize((550, 500))


def testGConsole():
    app = wx.App()
    frame = GConsoleFrame(parent = None)
    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    testGConsole()
