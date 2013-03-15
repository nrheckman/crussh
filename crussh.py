#!/usr/bin/env python

# A cssh replacement written in Python / GTK.
# (c)2012 - Graeme Humphries <graeme@sudo.ca>.
# Released under the GPL, version 3: http://www.gnu.org/licenses/

# Requires: python-gtk2 python-vte

import sys
import math
import json
import os.path

try:
    import gtk
except:
    print >>sys.stderr, "Missing Python GTK2 bindings."
    sys.exit(1)

try:
    import vte
except:
    print >>sys.stderr, "Missing Python VTE bindings."
    sys.exit(1)


### Config Dialog ###
class CruSSHConf:
    ### State Vars ###
    Config = {}
    MainWin = gtk.Window()

    ### Signal Hooks ###
    def save_hook(self, discard, save_func):
        self.MainWin.destroy()
        if save_func is not None:
            save_func(self.Config)

    def font_hook(self, fontbutton):
        self.Config["font"] = fontbutton.get_font_name()

    def width_hook(self, spinbutton):
        self.Config["min-width"] = spinbutton.get_value_as_int()

    def height_hook(self, spinbutton):
        self.Config["min-height"] = spinbutton.get_value_as_int()

    ### GUI Objects ###
    def initGUI(self, save_func=None):
        self.MainWin.set_modal(True)
        self.MainWin.props.allow_grow = False

        MainBox = gtk.VBox(spacing=5)
        MainBox.props.border_width = 5
        self.MainWin.add(MainBox)

        TermConfFrame = gtk.Frame(label="Terminal Options")
        TermConfTable = gtk.Table(3, 2)
        TermConfTable.props.border_width = 5
        TermConfTable.props.row_spacing = 5
        TermConfTable.props.column_spacing = 5
        TermConfFrame.add(TermConfTable)
        MainBox.pack_start(TermConfFrame)

        TermConfTable.attach(gtk.Label("Font:"), 1, 2, 1, 2, gtk.EXPAND)
        FontConf = gtk.FontButton(fontname=self.Config["font"])
        FontConf.connect("font-set", self.font_hook)
        TermConfTable.attach(FontConf, 2, 3, 1, 2, gtk.EXPAND)

        SizeBox = gtk.HBox()
        SizeBox.props.spacing = 5
        TermConfTable.attach(SizeBox, 1, 3, 2, 3)
        SizeBox.pack_start(gtk.Label("Min Width:"), fill=False, expand=False)
        WidthEntry = gtk.SpinButton(gtk.Adjustment(value=self.Config["min-width"], lower=1, upper=9999, step_incr=1))
        WidthEntry.connect("value-changed", self.width_hook)
        SizeBox.pack_start(WidthEntry, fill=False, expand=False)
        SizeBox.pack_start(gtk.Label("Min Height:"), fill=False, expand=False)
        HeightEntry = gtk.SpinButton(gtk.Adjustment(value=self.Config["min-height"], lower=1, upper=9999, step_incr=1))
        HeightEntry.connect("value-changed", self.height_hook)
        SizeBox.pack_start(HeightEntry, fill=False, expand=False)

        ConfirmBox = gtk.HBox(spacing=5)
        CancelButton = gtk.Button(stock=gtk.STOCK_CANCEL)
        ConfirmBox.pack_start(CancelButton, fill=False)
        SaveButton = gtk.Button(stock=gtk.STOCK_SAVE)
        ConfirmBox.pack_start(SaveButton, fill=False)
        MainBox.pack_start(ConfirmBox, fill=False, expand=False)

        # wire up behaviour
        CancelButton.connect("clicked", lambda discard: self.MainWin.destroy())
        SaveButton.connect("clicked", self.save_hook, save_func)

        self.MainWin.show_all()

    # we'll wire up a supplied save_func that takes the Config dict as an argument.
    def __init__(self, config=None, save_func=None):
        if config is not None:
            self.Config = config

        self.initGUI(save_func)


### CruSSH! ###
class CruSSH:
    ### Config Vars ###
    # config defaults
    Config = {
        "min-width": 80,
        "min-height": 24,
        "font": "Ubuntu Mono Bold 10"
        }

    ### State Vars ###
    Terminals = {}
    TermMinWidth = 1
    TermMinHeight = 1

    ### GUI Objects ###
    MainWin = gtk.Window()
    ScrollWin = gtk.ScrolledWindow()
    LayoutTable = gtk.Table()
    EntryBox = gtk.Entry()
    Clipboard = gtk.Clipboard()
    ActiveHostsMenu = gtk.Menu()

    ### Methods ###
    def reflowTable(self, cols=1, rows=1):
        # empty table and re-size
        hosts = sorted(self.Terminals.keys(), reverse=True)
        for host in hosts:
            if self.Terminals[host].parent == self.LayoutTable:
                self.LayoutTable.remove(self.Terminals[host])
        self.LayoutTable.resize(rows, cols)
        # layout terminals
        for row in range(rows):
            for col in range(cols):
                if len(hosts) > 0:
                    host = hosts.pop()
                    self.Terminals[host].set_size(self.Config["min-width"], self.Config["min-height"])
                    self.Terminals[host].set_tooltip_text(host)
                    self.LayoutTable.attach(self.Terminals[host], col, col + 1, row, row + 1)

    def reflow(self, force=False):
        # reconfigure before updating rows and columns
        self.configTerminals()

        num_terms = len(self.Terminals.keys())
        if num_terms < 1:
            gtk.main_quit()
            # main_quit desn't happen immediately
            return False
        size = self.MainWin.allocation
        cols = int(math.floor((size.width + self.LayoutTable.props.column_spacing) / float(self.TermMinWidth)))
        if cols < 1 or num_terms == 1:
            cols = 1
        elif cols > num_terms:
            cols = num_terms
        rows = int(math.ceil(num_terms / float(cols)))
        if rows < 1:
            rows = 1
        if (self.LayoutTable.props.n_columns != cols) or (self.LayoutTable.props.n_rows != rows) or force:
            self.reflowTable(cols, rows)
        self.MainWin.show_all()

    def configTerminals(self):
        for host in self.Terminals:
            terminal = self.Terminals[host]
            # -1 == infinite scrollback
            terminal.set_scrollback_lines(-1)
            terminal.set_size(self.Config["min-width"], self.Config["min-height"])
            terminal.set_font_from_string(self.Config["font"])
            self.TermMinWidth = (terminal.get_char_width() * self.Config["min-width"]) + terminal.get_padding()[0]
            self.TermMinHeight = (terminal.get_char_height() * self.Config["min-height"]) + terminal.get_padding()[1]

    def removeTerminal(self, terminal):
        # brute force search since we don't actually know the hostname from the
        # terminal object. this is an infrequent operation, so it should be fine.
        for menuitem in self.ActiveHostsMenu.get_children():
            if terminal.get_tooltip_text() == menuitem.get_label():
                self.ActiveHostsMenu.remove(menuitem)
        for host in self.Terminals.keys():
            if terminal == self.Terminals[host]:
                self.LayoutTable.remove(self.Terminals[host])
                print("Disconnected from " + host)
                del self.Terminals[host]

        self.reflow(force=True)

    def initGUI(self):
        theme = gtk.icon_theme_get_default()
        if theme.has_icon("terminal"):
            icon = theme.lookup_icon("terminal", 128, flags=gtk.ICON_LOOKUP_USE_BUILTIN)
            if icon is not None:
                gtk.window_set_default_icon(icon.load_icon())
        self.MainWin.set_title("crussh: " + ' '.join(self.Terminals.keys()))
        self.MainWin.set_role(role="crussh_main_win")
        self.MainWin.connect("delete-event", lambda window, event: gtk.main_quit())
        MainVBox = gtk.VBox()
        self.MainWin.add(MainVBox)

        MainMenuBar = gtk.MenuBar()
        MainVBox.pack_start(MainMenuBar, fill=True, expand=False)

        FileItem = gtk.MenuItem(label="File")
        FileMenu = gtk.Menu()
        FileItem.set_submenu(FileMenu)
        QuitItem = gtk.MenuItem(label="Quit")
        QuitItem.connect("activate", lambda discard: gtk.main_quit())
        FileMenu.append(QuitItem)
        MainMenuBar.append(FileItem)

        EditItem = gtk.MenuItem(label="Edit")
        EditMenu = gtk.Menu()
        EditItem.set_submenu(EditMenu)

        def toggle_func(checkitem, host):
            self.Terminals[host].copy_input = checkitem.get_active()
        ActiveHostsItem = gtk.MenuItem(label="Active Hosts")
        ActiveHostsItem.set_submenu(self.ActiveHostsMenu)
        hosts = sorted(self.Terminals.keys(), reverse=False)
        for host in hosts:
            hostitem = gtk.CheckMenuItem(label=host)
            hostitem.set_active(True)
            hostitem.connect("toggled", toggle_func, host)
            self.ActiveHostsMenu.append(hostitem)

        EditMenu.append(ActiveHostsItem)
        PrefsItem = gtk.MenuItem(label="Preferences")

        def save_func(new_config):
            self.Config = new_config
            self.reflow(force=True)
            # save to file last, so it doesn't hold up other GUI actions
            conf_json = json.dumps(self.Config, sort_keys=True, indent=4)
            try:
                conf_file = open(os.path.expanduser("~/.crusshrc"), 'w')
                conf_file.write(conf_json)
                conf_file.close()
            except:
                pass
        PrefsItem.connect("activate", lambda discard: CruSSHConf(self.Config, save_func))
        EditMenu.append(PrefsItem)
        MainMenuBar.append(EditItem)

        self.ScrollWin.props.hscrollbar_policy = gtk.POLICY_NEVER
        self.ScrollWin.props.vscrollbar_policy = gtk.POLICY_ALWAYS
        self.ScrollWin.props.shadow_type = gtk.SHADOW_ETCHED_IN
        MainVBox.pack_start(self.ScrollWin)

        self.LayoutTable.set_homogeneous(True)
        self.LayoutTable.set_row_spacings(1)
        self.LayoutTable.set_col_spacings(1)
        self.ScrollWin.add_with_viewport(self.LayoutTable)
        self.ScrollWin.set_size_request(self.TermMinWidth, self.TermMinHeight)

        # don't display chars while typing.
        self.EntryBox.set_visibility(False)
        self.EntryBox.set_invisible_char(' ')

        # feed GNOME clipboard to all active terminals
        def feed_paste(widget):
            for host in self.Terminals:
                if self.Terminals[host].copy_input:
                    self.Terminals[host].paste_clipboard()
            self.EntryBox.props.buffer.delete_text(0, -1)

        # forward key events to all terminals with copy_input set
        def feed_input(widget, event):
            self.EntryBox.props.buffer.delete_text(0, -1)
            # check for paste key shortcut (ctl-shift-v)
            if (event.type == gtk.gdk.KEY_PRESS) \
            and (event.state & gtk.gdk.CONTROL_MASK == gtk.gdk.CONTROL_MASK) \
            and (event.state & gtk.gdk.SHIFT_MASK == gtk.gdk.SHIFT_MASK) \
            and (event.keyval == gtk.gdk.keyval_from_name('V')):
                feed_paste(widget)
            else:
                # propagate to every terminal
                for host in self.Terminals:
                    t_event = event.copy()
                    if self.Terminals[host].copy_input:
                        self.Terminals[host].event(t_event)
            # this stops regular handler from firing, switching focus.
            return True

        def click_handler(widget, event):
            # if middle click
            if event.button == 2:
                feed_input(widget, event)

        self.EntryBox.connect("key_press_event", feed_input)
        self.EntryBox.connect("key_release_event", feed_input)
        self.EntryBox.connect("paste_clipboard", feed_paste)
        self.EntryBox.connect("button_press_event", click_handler)
        MainVBox.pack_start(self.EntryBox, False, False)

        # reflow layout on size change.
        self.MainWin.connect("size-allocate", lambda widget, allocation: self.reflow())

        # give EntryBox default focus on init
        self.EntryBox.props.has_focus = True

    def __init__(self, hosts, ssh_cmd="/usr/bin/ssh", ssh_args=None):
        # load existing config file, if present
        try:
            # merge dicts to allow upgrade from old configs
            new_config = json.load(open(os.path.expanduser('~/.crusshrc')))
            self.Config.update(new_config)
        except:
            pass

        def handle_copy_paste(widget, event):
            self.EntryBox.props.buffer.delete_text(0, -1)
            # check for paste key shortcut (ctl-shift-v)
            if (event.type == gtk.gdk.KEY_PRESS) \
            and (event.state & gtk.gdk.CONTROL_MASK == gtk.gdk.CONTROL_MASK) \
            and (event.state & gtk.gdk.SHIFT_MASK == gtk.gdk.SHIFT_MASK) \
            and (event.keyval == gtk.gdk.keyval_from_name('V')):
                widget.paste_clipboard()
                return True
            elif (event.type == gtk.gdk.KEY_PRESS) \
            and (event.state & gtk.gdk.CONTROL_MASK == gtk.gdk.CONTROL_MASK) \
            and (event.state & gtk.gdk.SHIFT_MASK == gtk.gdk.SHIFT_MASK) \
            and (event.keyval == gtk.gdk.keyval_from_name('C')):
                widget.copy_clipboard()
                return True
        # init all terminals
        for host in hosts:
            terminal = vte.Terminal()
            # TODO: disable only this terminal widget on child exit
            # v.connect("child-exited", lambda term: gtk.main_quit())
            cmd_str = ssh_cmd
            if ssh_args is not None:
                cmd_str += " " + ssh_args
            cmd_str += " " + host
            cmd = cmd_str.split(' ')
            terminal.fork_command(command=cmd[0], argv=cmd)
            # track whether we mirror output to this terminal
            terminal.copy_input = True
            # attach copy/paste handler
            terminal.connect("key_press_event", handle_copy_paste)
            self.Terminals[host] = terminal

            # hook terminals so they reflow layout on exit
            self.Terminals[host].connect("child-exited", self.removeTerminal)
        # configure all terminals
        self.configTerminals()
        # reflow after reconfig for font size changes
        self.initGUI()
        self.reflow(force=True)

if __name__ == "__main__":
    import argparse

    ### Parse CLI Args ###
    parser = argparse.ArgumentParser(
        description="Connect to multiple hosts in parallel.",
        usage="%(prog)s [OPTIONS] [--] HOST [HOST ...]",
        epilog="* NOTE: You can pass options to ssh if you add '--' before your list of hosts")
    parser.add_argument("--ssh", dest='ssh', default="/usr/bin/ssh",
        help="specify the SSH executable to use (default: %(default)s)")
    (args, hosts) = parser.parse_known_args()

    if len(hosts) == 0:
        parser.print_usage()
        parser.exit(2)

    try:
        offset = hosts.index("--")
    except:
        ssh_args = None
    else:
        ssh_args = " ".join(hosts[0:offset])
        hosts = hosts[offset + 1:]

    ### Start Execution ###
    crussh = CruSSH(hosts, args.ssh, ssh_args)
    gtk.main()
