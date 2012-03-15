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
	print(sys.stderr, "Missing Python GTK2 bindings. (apt-get install python-gtk2)")
try:
	import vte
except:
	error = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
		"Missing Python VTE bindings. (apt-get install python-vte)")
	error.run()
	sys.exit(1)

### Parse CLI Args ###
parser = argparse.ArgumentParser(description="Connect to multiple servers in parallel.")
parser.add_argument('hosts', metavar='HOST', nargs='+',
	help="Host(s) to connect to.")
parser.add_argument('-l', '--login', dest='login', default=getpass.getuser(),
	help="Login name to use.")
parser.add_argument('-p', '--port', dest='port', type=int, default=22,
	help="Alternate SSH port to use.")
parser.add_argument('-s', '--fontsize', dest='fontsize', type=int, default=10,
	help="Font size to use. (default=10)")

args = parser.parse_args()

### Global Vars ###
Terminals = {}
TermMinWidth = 1
TermMinHeight = 1

### Configure Terminals ###
for host in args.hosts:
	terminal = vte.Terminal()
	terminal.set_size(80, 24)
	terminal.set_font_from_string("Ubuntu Mono Bold " + str(args.fontsize))
	TermMinWidth = (terminal.get_char_width() * 80) + terminal.get_padding()[0]
	TermMinHeight = (terminal.get_char_height() * 24) + terminal.get_padding()[1]
	# TODO: disable only this terminal widget on child exit
	# v.connect("child-exited", lambda term: gtk.main_quit())
	cmd = "/usr/bin/ssh"
	cmd_args = ["-l '" + args.login + "'", "-p " + str(args.port), host]
	terminal.fork_command(cmd, cmd_args)
	Terminals[host] = terminal

### Utility Functions and Vars ###
def reflowTable(cols=1, rows=1):
	# empty table and re-size
	for host in Terminals:
		Table.remove(Terminals[host])
	Table.resize(rows, cols)
	# layout terminals
	hosts = sorted(args.hosts, reverse=True)
	for row in range(rows):
		for col in range(cols):
			if len(hosts) > 0:
				host = hosts.pop()
				Table.attach(Terminals[host], col, col+1, row, row+1)
				Terminals[host].set_size(80, 24)

def reflow():
	size = MainWin.allocation
	cols = int(math.floor((size.width + Table.props.column_spacing) / TermMinWidth))
	if cols < 1 or len(args.hosts) == 1:
		cols = 1
	rows = int(math.ceil(len(Terminals)/cols))
	if rows < 1:
		rows = 1
	if (Table.props.n_columns != cols) or (Table.props.n_rows != rows):
		reflowTable(cols, rows)	
	MainWin.show_all()

### Setup GTK Interface ###
MainWin = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
MainWin.set_title("crussh: " + ' '.join(args.hosts))
MainWin.set_role(role="crussh_main_win")
MainWin.connect("delete-event", lambda window, event: gtk.main_quit())

ScrollWin = gtk.ScrolledWindow()
ScrollWin.props.hscrollbar_policy = gtk.POLICY_NEVER
ScrollWin.props.vscrollbar_policy = gtk.POLICY_ALWAYS
ScrollWin.props.shadow_type = gtk.SHADOW_ETCHED_IN

Table = gtk.Table()
Table.set_homogeneous(True)
Table.set_row_spacings(1)
Table.set_col_spacings(1)
ScrollWin.add_with_viewport(Table)
ScrollWin.set_size_request(TermMinWidth, TermMinHeight)

EntryBox = gtk.Entry()
# don't display chars while typing.
EntryBox.set_visibility(False)
EntryBox.set_invisible_char(' ')
def feed_input(widget, event):
	if event.type in [gtk.gdk.KEY_PRESS, gtk.gdk.KEY_RELEASE]:
		# erase buffer on every entry, so that passwords aren't revealed
		EntryBox.props.buffer.delete_text(0, -1)
		# propagate to every terminal
		for host in Terminals:
			t_event = event.copy()
			Terminals[host].event(t_event)
		# this stops regular handler from firing, switching focus.
		return True
EntryBox.connect("key_press_event", feed_input)
EntryBox.connect("key_release_event", feed_input)

VBox = gtk.VBox()
VBox.pack_start(ScrollWin)
VBox.pack_start(EntryBox, False, False)
MainWin.add(VBox)

# reflow layout on size change.
def resize_event_handler(widget, allocation):
	reflow()
MainWin.connect("size-allocate", lambda widget, allocation: reflow())

### Start Execution ###
reflowTable()
reflow()
gtk.main()
