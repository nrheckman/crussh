#!/usr/bin/env python

# A cssh replacement written in Python / GTK.
# (c)2012 - Graeme Humphries <graeme@sudo.ca>.
# Released under the GPL, version 3: http://www.gnu.org/licenses/

# Requires: python-gtk2 python-vte

import sys
import argparse
import math
import json
try:
	import gtk
except:
	print(sys.stderr, "Missing Python GTK2 bindings.")
try:
	import vte
except:
	error = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
		"Missing Python VTE bindings.")
	error.run()
	sys.exit(1)

### Parse CLI Args ###
parser = argparse.ArgumentParser(description="Connect to multiple servers in parallel.")
parser.add_argument('hosts', metavar='HOST', nargs='+',
	help="Host(s) to connect to.")
parser.add_argument('-l', '--login', dest='login', default=None,
	help="Login name to use.")
parser.add_argument('-p', '--port', dest='port', type=int, default=None,
	help="Alternate SSH port to use.")
parser.add_argument('-s', '--fontsize', dest='fontsize', type=int, default=10,
	help="Font size to use. (default=10)")

args = parser.parse_args()

### Config Dialog ###
class CruSSHConf:
	### State Vars ###
	Config = {}
	MainWin = gtk.Window()

	### Signal Hooks ###
	def destroy_hook(self, discard, save_func):
		self.MainWin.destroy()
		if save_func != None:
			save_func(self.Config)

	def font_hook(self, fontbutton):
		self.Config["font"] = fontbutton.get_font_name()

	def opacity_hook(self, range):
		self.Config["opacity"] = range.get_value()

	### GUI Objects ###
	def initGUI(self, save_func = None):
		self.MainWin.set_modal(True)
		self.MainWin.props.allow_grow = False

		MainBox = gtk.VBox(spacing=5)
		MainBox.props.border_width = 5
		self.MainWin.add(MainBox)
		
		TermConfFrame = gtk.Frame(label="Terminal Options")
		TermConfTable = gtk.Table(2, 2)
		TermConfTable.props.border_width = 5
		TermConfTable.props.row_spacing = 5
		TermConfTable.props.column_spacing = 5
		TermConfFrame.add(TermConfTable)
		MainBox.pack_start(TermConfFrame)

		FontLabel = gtk.Label("Font:")
		TermConfTable.attach(FontLabel, 1, 2, 1, 2, gtk.EXPAND)
		FontConf = gtk.FontButton(fontname=self.Config["font"])
		FontConf.connect("font-set", self.font_hook)
		TermConfTable.attach(FontConf, 2, 3, 1, 2, gtk.EXPAND)

		OpacityLabel = gtk.Label("Opacity:")
		TermConfTable.attach(OpacityLabel, 1, 2, 2, 3, gtk.EXPAND)
		OpacityAdj = gtk.Adjustment(upper=65535, step_incr=1, value=self.Config["opacity"])
		OpacityScale = gtk.HScale(OpacityAdj)
		OpacityScale.set_draw_value(False)
		OpacityScale.connect("value-changed", self.opacity_hook)
		TermConfTable.attach(OpacityScale, 2, 3, 2, 3)

		ConfirmBox = gtk.HBox(spacing=5)
		CancelButton = gtk.Button(stock=gtk.STOCK_CANCEL)
		ConfirmBox.pack_start(CancelButton, fill=False)
		SaveButton = gtk.Button(stock=gtk.STOCK_SAVE)
		ConfirmBox.pack_start(SaveButton, fill=False)
		MainBox.pack_start(ConfirmBox, fill=False, expand=False)
		
		# wire up behaviour
		CancelButton.connect("clicked", lambda discard: self.MainWin.destroy())
		SaveButton.connect("clicked", self.destroy_hook, save_func)

		self.MainWin.show_all()

	# we'll wire up a supplied save_func that takes the Config dict as an argument.
	def __init__(self, config=None, save_func=None):
		if config != None:
			self.Config = config

		self.initGUI(save_func)

### CruSSH! ###
class CruSSH:
	### Config Vars ###
	# config defaults
	Config = {
		"login": None,
		"port": None,
		"font": "Ubuntu Mono Bold 10",
		"opacity": 65535
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
					self.Terminals[host].set_size(80, 24)
					self.LayoutTable.attach(self.Terminals[host], col, col+1, row, row+1)

	def reflow(self, force=False):
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
		rows = int(math.ceil(num_terms/float(cols)))
		if rows < 1:
			rows = 1
		if (self.LayoutTable.props.n_columns != cols) or (self.LayoutTable.props.n_rows != rows) or force:
			self.reflowTable(cols, rows)	
		self.MainWin.show_all()

	def configTerminals(self):
		for host in self.Terminals:
			terminal = self.Terminals[host]
			terminal.set_size(80, 24)
			terminal.set_font_from_string(self.Config["font"])
			terminal.set_opacity(int(self.Config["opacity"]))
			self.TermMinWidth = (terminal.get_char_width() * 80) + terminal.get_padding()[0]
			self.TermMinHeight = (terminal.get_char_height() * 24) + terminal.get_padding()[1]

	def removeTerminal(self, terminal):
		# brute force search since we don't actually know the hostname from the
		# terminal object. this is an infrequent operation, so it should be fine.
		for host in self.Terminals.keys():
			if terminal == self.Terminals[host]:
				self.LayoutTable.remove(self.Terminals[host])
				del self.Terminals[host]
		self.reflow(force=True)

	def initGUI(self):
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
		PrefsItem = gtk.MenuItem(label="Preferences")
		def save_func(new_config):
			self.Config = new_config
			self.configTerminals()
			self.reflow()
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
		# forward key events to all terminals
		def feed_input(widget, event):
			if event.type in [gtk.gdk.KEY_PRESS, gtk.gdk.KEY_RELEASE]:
				# erase buffer on every entry, so that passwords aren't revealed
				self.EntryBox.props.buffer.delete_text(0, -1)
				# propagate to every terminal
				for host in self.Terminals:
					t_event = event.copy()
					self.Terminals[host].event(t_event)
				# this stops regular handler from firing, switching focus.
				return True
		self.EntryBox.connect("key_press_event", feed_input)
		self.EntryBox.connect("key_release_event", feed_input)
		MainVBox.pack_start(self.EntryBox, False, False)

		# reflow layout on size change.
		self.MainWin.connect("size-allocate", lambda widget, allocation: self.reflow())

		# give EntryBox default focus on init
		self.EntryBox.props.has_focus = True

	def __init__(self, hosts, login=None, port=None):
		# load existing config file, if present
		try:
			Config = json.load(open('~/.crusshrc'))
		except Exception as e:
			pass

		# init all terminals
		for host in hosts:
			terminal = vte.Terminal()
			# TODO: disable only this terminal widget on child exit
			# v.connect("child-exited", lambda term: gtk.main_quit())
			cmd_str = "/usr/bin/ssh"
			if self.Config["login"] != None:
				cmd_str += " -l " + args.login
			if self.Config["port"] != None:
				cmd_str += " -p " + str(args.port)
			cmd_str += " " + host
			cmd = cmd_str.split(' ')
			terminal.fork_command(command=cmd[0], argv=cmd)
			self.Terminals[host] = terminal

			# hook terminals so they reflow layout on exit
			self.Terminals[host].connect("child-exited", self.removeTerminal)
		# configure all terminals
		self.configTerminals()
		# reflow after reconfig for font size changes
		self.initGUI()
		self.reflow(force=True)

### Start Execution ###
crussh = CruSSH(args.hosts, args.login, args.port)
gtk.main()
