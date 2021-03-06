# -*- coding: utf-8 -*-

'''
Copyright (c) 2019 Colin Curtain

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Author: Colin Curtain (ccbogel)
https://github.com/ccbogel/QualCoder
https://qualcoder.wordpress.com/
'''

from copy import copy
import datetime
import logging
from lxml import etree
from operator import itemgetter
import os
import re
import shutil
import sqlite3
import sys
import traceback
import uuid

import zipfile

from PyQt5 import QtWidgets

path = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)


def exception_handler(exception_type, value, tb_obj):
    """ Global exception handler useful in GUIs.
    tb_obj: exception.__traceback__ """
    tb = '\n'.join(traceback.format_tb(tb_obj))
    text = 'Traceback (most recent call last):\n' + tb + '\n' + exception_type.__name__ + ': ' + str(value)
    print(text)
    logger.error(_("Uncaught exception: ") + text)
    #QtWidgets.QMessageBox.critical(None, _('Uncaught Exception'), text)


class Rqda_import():
    """ Import an RQDA database into a new QualCoder database. """

    parent_textEdit = None
    app = None
    conn = None

    def __init__(self, app, parent_textEdit):
        super(Rqda_import, self).__init__()

        sys.excepthook = exception_handler
        self.app = app
        self.parent_textEdit = parent_textEdit

        self.file_path, ok = QtWidgets.QFileDialog.getOpenFileName(None,
            _('Select RQDA file'), self.app.settings['directory'], "*.rqda")
        if not ok or self.file_path == "":
            return
        self.conn = sqlite3.connect(self.file_path)
        try:
            self.import_data()
            self.parent_textEdit.append(_("Data imported from ") + self.file_path)
            self.parent_textEdit.append(_("File categories are not imported from RQDA"))
        except:
            self.parent_textEdit.append(_("Data import unsuccessful from ") + self.file_path)

    def convert_date(self, r_date):
        """ Convert RQDA date format from:
        Mon Oct 28 08:11:36 2019 to: yyyy-mm-dd hh:mm:ss

        param: rqda formatted date
        return: standard format date
        """

        yyyy = r_date[-4:]
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        mm = str(months.index(r_date[4:7]) + 1)
        if len(mm) == 1:
            mm = "0" + mm
        # TODO check if day is ALWAYS 2 digits
        dd = r_date[8:10]
        hh_mm_ss = r_date[12:19]
        return yyyy + "-" + mm + "-" + dd + " " + hh_mm_ss

    def import_data(self):
        """  """

        r_cur = self.conn.cursor()
        q_cur = self.app.conn.cursor()

        r_cur.execute("select memo from project")
        res = r_cur.fetchone()
        q_cur.execute("update project set memo=?", (res[0], ))
        r_cur.execute("select id,name, file, memo, owner, date from source")
        res = r_cur.fetchall()
        for r in res:
            q_cur.execute("insert into source (id, name, fulltext,memo, owner, date, mediapath) values (?,?,?,?,?,?,?)",
                [r[0], r[1], r[2], r[3], r[4], self.convert_date(r[5]), None])
        r_cur.execute("select fid,position,annotation, owner, date from annotation")
        res = r_cur.fetchall()
        for r in res:
            q_cur.execute("insert into annotation (fid, pos0, pos1, memo, owner, date) values (?,?,?,?,?,?)",
                [r[0], r[1], r[1] + 1, r[2], r[3], self.convert_date(r[4])])
        r_cur.execute("select name,journal, owner, date from journal")
        res = r_cur.fetchall()
        for r in res:
            q_cur.execute("insert into journal (name, jentry, owner, date) values (?,?,?,?)",
                [r[0], r[1], r[2], self.convert_date(r[3])])
        r_cur.execute("select id, name, memo, owner, date from cases")
        res = r_cur.fetchall()
        for r in res:
            q_cur.execute("insert into cases (caseid, name, memo, owner, date) values (?,?,?,?,?)",
                [r[0], r[1], r[2], r[3], self.convert_date(r[4])])
        r_cur.execute("select catid, name, memo, owner, date from codecat")
        res = r_cur.fetchall()
        for r in res:
            # there are no supercatids in rqda
            q_cur.execute("insert into code_cat (catid,name, memo, owner, date,supercatid) values (?,?,?,?,?,?)",
                [r[0], r[1], r[2], r[3], self.convert_date(r[4]), None])
        # get catids for each code cid
        r_cur.execute("select cid, catid from treecode")
        treecodes = r_cur.fetchall()
        r_cur.execute("select id, name, memo,color, owner, date from freecode")
        res = r_cur.fetchall()
        for r in res:
            treecode = None
            for t in treecodes:
                if t[0] == r[0]:
                    treecode = t[1]  # the corresponding catid
            q_cur.execute("insert into code_name (cid, catid,name, memo,color, owner, date) values (?,?,?,?,?,?,?)",
                [r[0],treecode, r[1], r[2], r[3], r[4], self.convert_date(r[5])])
        r_cur.execute("select cid, fid, seltext,selfirst,selend,memo, owner, date from coding")
        res = r_cur.fetchall()
        for r in res:
            q_cur.execute("insert into code_text (cid, fid,seltext, pos0,pos1,memo, owner, date) values (?,?,?,?,?,?,?,?)",
                [r[0], r[1], r[2], r[3], r[4], r[5], r[6], self.convert_date(r[7])])
        r_cur.execute("select cid, fid, seltext,selfirst,selend,memo, owner, date from coding2")
        res = r_cur.fetchall()
        for r in res:
            q_cur.execute("insert into code_text (cid, fid,seltext, pos0,pos1,memo, owner, date) values (?,?,?,?,?,?,?,?)",
                [r[0], r[1], r[2], r[3], r[4], r[5], r[6], self.convert_date(r[7])])

        # attribute class = character or numeric
        r_cur.execute("select distinct variable from caseAttr")
        case_attr = r_cur.fetchall()
        r_cur.execute("select name,class,memo, owner, date from attributes")
        res = r_cur.fetchall()
        for r in res:
            # default to a file attribute unless it is a case attribute
            caseOrFile = "file"
            for c in case_attr:
                if c[0] == r[0]:
                    caseOrFile = "case"
            q_cur.execute("insert into attribute_type (name, valuetype,caseOrFile,memo, owner, date) values (?,?,?,?,?,?)",
                [r[0], r[1], caseOrFile, r[2], r[3], self.convert_date(r[4])])
        r_cur.execute("select variable, value, caseID, owner, date from caseAttr")
        res = r_cur.fetchall()
        for r in res:
            q_cur.execute("insert into attribute (name,value, id, owner,date, attr_type) values(?,?,?,?,?,?)",
                [r[0], r[1], r[2], r[3], self.convert_date(r[4]), "case"])
        r_cur.execute("select variable, value, fileID, owner, date from fileAttr")
        res = r_cur.fetchall()
        for r in res:
            q_cur.execute("insert into attribute (name,value, id, owner,date, attr_type) values(?,?,?,?,?,?)",
                [r[0], r[1], r[2], r[3], self.convert_date(r[4]), "file"])
        r_cur.execute("select caseid,fid,selfirst,selend, owner, memo,date from caselinkage")
        res = r_cur.fetchall()
        for r in res:
            q_cur.execute("insert into case_text (caseid,fid,pos0,pos1,owner,memo, date) values(?,?,?,?,?,?,?)",
                [r[0], r[1], r[2], r[3], r[4], r[5], self.convert_date(r[6])])
        self.app.conn.commit()

"""
 done project (databaseversion text, date text,dateM text, memo text,about text, imageDir text
 done source (name text, id integer, file text, memo text, owner text, date text, dateM text, status integer
 done annotation (fid integer,position integer,annotation text, owner text, date text,dateM text, status integer
 done journal (name text, journal text, date text, dateM text, owner text,status integer
 done cases  (name text, memo text, owner text,date text,dateM text, id integer, status integer
 done codecat  (name text, cid integer, catid integer, owner text, date text, dateM text,memo text, status integer
 done coding  (cid integer, fid integer,seltext text, selfirst real, selend real, status integer, owner text, date text, memo text
 done coding2  (cid integer, fid integer,seltext text, selfirst real, selend real, status integer, owner text, date text, memo text
 done freecode  (name text, memo text, owner text,date text,dateM text, id integer, status integer, color text
 donetreecode  (cid integer, catid integer, date text, dateM text, memo text, status integer, owner text
 done attributes (name text, status integer, date text, dateM text, owner text,memo text, class text
 done fileAttr (variable text, value text, fileID integer, date text, dateM text, owner text, status integer
 done caseAttr (variable text, value text, caseID integer, date text, dateM text, owner text, status integer
 done caselinkage  (caseid integer, fid integer, selfirst real, selend real, status integer, owner text, date text, memo text

 treefile  (fid integer, catid integer, date text,dateM text, memo text, status integer,owner text
 filecat  (name text,fid integer, catid integer, owner text, date text, dateM text,memo text, status integer
 """

