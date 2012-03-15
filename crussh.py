#!/usr/bin/env python

# A cssh replacement written in Python / GTK.
# (c)2012 - Graeme Humphries <graeme@sudo.ca>.
# Released under the GPL, version 3: http://www.gnu.org/licenses/

# Requires: python-gtk2 python-vte

import sys
import argparse
import getpass
import math
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

### CruSSH! ###
class CruSSH:
	### State Vars ###
	Terminals = {}
	TermMinWidth = 1
	TermMinHeight = 1

	### GUI Objects ###
	MainWin = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
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
		num_terms = len(self.Terminals)
		if num_terms < 1:
			gtk.main_quit()
		size = self.MainWin.allocation
		cols = int(math.floor((size.width + self.LayoutTable.props.column_spacing) / float(self.TermMinWidth)))
		if cols < 1 or num_terms == 1:
			cols = 1
		rows = int(math.ceil(num_terms/float(cols)))
		if rows < 1:
			rows = 1
		if (self.LayoutTable.props.n_columns != cols) or (self.LayoutTable.props.n_rows != rows) or force:
			self.reflowTable(cols, rows)	
		self.MainWin.show_all()

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

		self.ScrollWin.props.hscrollbar_policy = gtk.POLICY_NEVER
		self.ScrollWin.props.vscrollbar_policy = gtk.POLICY_ALWAYS
		self.ScrollWin.props.shadow_type = gtk.SHADOW_ETCHED_IN

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

		VBox = gtk.VBox()
		VBox.pack_start(self.ScrollWin)
		VBox.pack_start(self.EntryBox, False, False)
		self.MainWin.add(VBox)

		# reflow layout on size change.
		self.MainWin.connect("size-allocate", lambda widget, allocation: self.reflow())

		# give EntryBox default focus on init
		self.EntryBox.props.has_focus = True

	def __init__(self, hosts):
		# init all terminals
		for host in hosts:
			terminal = vte.Terminal()
			terminal.set_size(80, 24)
			terminal.set_font_from_string("Ubuntu Mono Bold " + str(args.fontsize))
			self.TermMinWidth = (terminal.get_char_width() * 80) + terminal.get_padding()[0]
			self.TermMinHeight = (terminal.get_char_height() * 24) + terminal.get_padding()[1]
			# TODO: disable only this terminal widget on child exit
			# v.connect("child-exited", lambda term: gtk.main_quit())
			cmd_str = "/usr/bin/ssh"
			if args.login != None:
				cmd_str += " -l " + args.login
			if args.port != None:
				cmd_str += " -p " + str(args.port)
			cmd_str += " " + host
			cmd = cmd_str.split(' ')
			terminal.fork_command(command=cmd[0], argv=cmd)
			self.Terminals[host] = terminal

			# hook terminals so they reflow layout on exit
			self.Terminals[host].connect("child-exited", self.removeTerminal)

		self.initGUI()
		self.reflow()

### Start Execution ###
crussh = CruSSH(args.hosts)
gtk.main()
