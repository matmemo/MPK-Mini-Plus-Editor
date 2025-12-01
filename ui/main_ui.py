#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# MPK-Mini-Plus-editor
# Copyright (C) 2025  Jesse G
# Original work derived from
# MPK M2-editor
# Copyright (C) 2017  Damien Picard dam.pic AT free.fr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Create the UI."""

import sys

from core.config import Config
from core.midi_interface import AkaiMPKPlus
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtWidgets import QGroupBox, QMessageBox

from ui.autofill import UiAutoFill
from ui.menubar import MenuBar
from ui.options import Options
from ui.programmes import Programmes


class UiMainWindow(QtWidgets.QMainWindow):
    """The main UI window."""

    def __init__(self, *args, **kwargs):
        """Init the UI and connect to controler."""
        super().__init__(*args, **kwargs)
        self.setObjectName('main_window')
        self.resize(1250, 1000)
        self.setStyleSheet("""
          * {
             font: 9pt;
            }
          QGroupBox {
            padding: 2px;
            padding-top: 20px;
          }""")

        self.autofill_ui = UiAutoFill(self)

        self.midi = AkaiMPKPlus()
        if not self.midi.connected:
            self.show_popup_controller_not_found()

        scroll_container = QtWidgets.QWidget()
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_container)
        self.setCentralWidget(scroll_area)

        layout = QtWidgets.QGridLayout(scroll_container)
        layout.setContentsMargins(-1, -1, -1, 0)
        layout.setObjectName('main_grid_layout')

        menubar = MenuBar([self.file_open, self.file_save_as], [
            self.copy_to, self.autofill_ui.show
        ])
        self.setMenuBar(menubar)

        self.programmes = Programmes(scroll_container)
        self.progs = self.programmes.progs
        layout.addWidget(self.programmes, 0, 0, 1, 1)

        options = Options({
            'current': (self.get_active_programme, self.send_active_programme),
            'all': (self.get_all_programmes, self.send_all_programmes),
            'ram': (self.get_ram, self.send_ram)
        })
        layout.addLayout(options, 1, 0, 1, 1)

        self.retranslate_ui()
        self.programmes.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(self)

    def show_popup_controller_not_found(self):
        """Show popup if midi not connected."""
        _translate = QtCore.QCoreApplication.translate
        while not self.midi.connected:
            msg = QMessageBox()
            msg.setWindowTitle(_translate('popup', 'MPK Mini Plus Editor'))
            msg.setText(_translate('popup', 'Controller not found'))
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setStandardButtons(QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Close)
            msg.setDefaultButton(QMessageBox.StandardButton.Retry)

            ret = msg.exec()

            if ret == QMessageBox.StandardButton.Close:
                sys.exit()
            else:
                self.midi = AkaiMPKPlus()

    def get_active_tab_index(self):
        """Get the current active tab."""
        return self.programmes.currentIndex()

    def fill_tab(self, config, p_i=None):
        """Fill the tab with config information."""
        prog = self.progs[p_i]
        prog.findChild(QtWidgets.QVBoxLayout, 'misc').fill(config)
        prog.findChild(QGroupBox, 'pads_group_box').fill(config)
        prog.findChild(QGroupBox, 'knobs_group_box').fill(config)

    def get_tab_programme(self, config, p_i):
        """Create a config from the programme p_i."""
        prog = self.progs[p_i]
        config.add_values({'programme': p_i + 1})
        config.add_values(prog.findChild(QtWidgets.QVBoxLayout, 'misc').values())
        config.add_values(prog.findChild(QGroupBox, 'pads_group_box').values())
        config.add_values(prog.findChild(QGroupBox, 'knobs_group_box').values())
        return config

    def get_all_programmes(self):
        """Get all programmes.

        Returns a list of programme configs.
        """
        configs = []
        for p_i in range(0, 8):
            config = self.get_programme(p_i + 1)
            self.fill_tab(config, p_i)
            configs.append(config)
        return configs

    def get_active_programme(self):
        """Get current programme.

        Returns a programme config.
        """
        p_i = self.get_active_tab_index()
        config = self.get_programme(p_i + 1)
        self.fill_tab(config, p_i)
        return config

    def get_ram(self):
        """Get current programme in RAM.

        Returns a programme config.
        """
        p_i = self.get_active_tab_index()
        config = self.get_programme(0)
        self.fill_tab(config, p_i)
        return config

    def get_programme(self, p_i):
        """Get programme p_i.

        Returns a programme config.
        """
        return self.midi.get_programme(p_i)

    def copy_to(self, p_to):
        """Copy programme to different tab."""
        p_from = self.get_active_tab_index()
        config = Config()
        conf = self.get_tab_programme(config, p_from)
        conf.pad_channel += 1
        conf.key_channel += 1
        self.fill_tab(conf, p_to - 1)

    def send_all_programmes(self):
        """Send all programmes."""
        for p_i in range(0, 8):
            self.send_programme(p_i)

    def send_active_programme(self):
        """Send currently active programme."""
        p_i = self.get_active_tab_index()
        self.send_programme(p_i)

    def send_programme(self, p_i):
        """Send p_i to correct slot."""
        config = Config()
        message = self.get_tab_programme(config, p_i)
        self.midi.send_midi_message(message.serialize())

    def send_ram(self):
        """Send current prog to RAM."""
        p_i = self.get_active_tab_index()
        config = Config()
        out_message = self.get_tab_programme(config, p_i)
        out_message.programme = 0
        self.midi.send_midi_message(out_message.serialize())

    def load_mpkminiplus(self, filepath):
        """Load a config file."""
        print('Loading', filepath)
        with open(filepath, 'rb') as f:
            conf = [int(i) for i in f.read()]
            config = Config()
            config.parse_config(conf)
            self.fill_tab(config, self.get_active_tab_index())

    def save_mpkminiplus(self, filepath):
        """Save a config file."""
        print('Saving', filepath)
        config = Config()
        conf = self.get_tab_programme(config, self.get_active_tab_index())
        with open(filepath, 'wb') as f:
            for b in conf.serialize():
                f.write(b.to_bytes(1, 'little'))

    def file_open(self):
        """Open a saved config file."""
        filename = QtWidgets.QFileDialog.getOpenFileName(None, 'Open file…', '',
                                                         'MPK mini Plus files (*.mpkminiplus)')
        if filename:
            if filename[0].endswith('.mpkminiplus'):
                self.load_mpkminiplus(filename[0])
            else:
                print('Unrecognized filetype')

    def file_save_as(self):
        """Save a config file."""
        filename = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file…', '',
                                                         'MPK mini Plus files (*.mpkminiplus)')
        if filename:
            if filename[0].endswith('.mpkminiplus'):
                self.save_mpkminiplus(filename[0])
            else:
                print('Unrecognized filetype')

    def retranslate_ui(self):
        """Create and translate all UI text elements."""
        _translate = QtCore.QCoreApplication.translate
        self.findChild(QtWidgets.QHBoxLayout, 'options').retranslate()
        self.findChild(QtWidgets.QMenuBar, 'menubar').retranslate()

        progs = self.findChild(QtWidgets.QTabWidget, 'programmes').findChildren(
            QtWidgets.QWidget, QRegularExpression('prog_*'))[::-1]
        for p_i, prog in enumerate(progs):

            prog.findChild(QtWidgets.QVBoxLayout, 'misc').retranslate()
            prog.findChild(QGroupBox, 'pads_group_box').retranslate()
            prog.findChild(QGroupBox, 'knobs_group_box').retranslate()

            self.programmes.setTabText(
                self.programmes.indexOf(prog),
                _translate('main_window', 'PROG') + ' ' + str(p_i + 1))


# are you feeling it mr crabs
