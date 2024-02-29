# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SIOSETools
                                 A QGIS plugin
 Este plugin permite consultar la cartografía SIOSE del IGN.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-10-18
        git sha              : $Format:%H$
        copyright            : (C) 2023 by IGN-UCLM
        email                : david.hernadez@uclm.es
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import sys, os, subprocess
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt import QtGui, QtWidgets
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem, QListWidgetItem, QFileDialog, QMessageBox
from qgis.PyQt.QtCore import QVariant
from qgis.core import *
from qgis.gui import QgsMessageBar
from osgeo import gdal, osr, ogr
import shutil
from . import siose_tools_definitions as SDefs


class SioseGpkgTools(object):
    def __init__(self,
                 iface,
                 gdal_error_handler,
                 siose_layer_names,
                 siose_hr_layer_names,
                 templates_path):
        self.iface = iface  # Save reference to the QGIS interface
        self.gdal_error_handler = gdal_error_handler
        self.siose_layer_names = siose_layer_names
        self.siose_hr_layer_names = siose_hr_layer_names
        self.str_last_error = ''
        self.templates_path = templates_path
        self.siose_codiige_qml_file = os.path.join(self.templates_path, SDefs.CONST_SIOSE_CODIIGE_QML_FILE_NAME)
        if not QFile.exists(self.siose_codiige_qml_file):
            raise ValueError(self.tr(u'No se encuentra el fichero QML de SIOSE:\n') + self.siose_codiige_qml_file)
        self.siose_hilucs_qml_file = os.path.join(self.templates_path, SDefs.CONST_SIOSE_HILUCS_QML_FILE_NAME)
        if not QFile.exists(self.siose_hilucs_qml_file):
            raise ValueError(self.tr(u'No se encuentra el fichero QML de SIOSE:\n') + self.siose_hilucs_qml_file)
        self.siose_hr_coverages_qml_file = os.path.join(self.templates_path,
                                                        SDefs.CONST_SIOSE_HR_COVERAGES_QML_FILE_NAME)
        if not QFile.exists(self.siose_hr_coverages_qml_file):
            raise ValueError(
                self.tr(u'No se encuentra el fichero QML de SIOSE AR:\n') + self.siose_hr_coverages_qml_file)
        self.siose_hr_uses_qml_file = os.path.join(self.templates_path, SDefs.CONST_SIOSE_HR_USES_QML_FILE_NAME)
        if not QFile.exists(self.siose_hr_uses_qml_file):
            raise ValueError(self.tr(u'No se encuentra el fichero QML de SIOSE AR:\n') + self.siose_hr_uses_qml_file)

    def check_model(self, fileName, siose_hr_selected, only_siose_model_layers, all_siose_model_layers):
        self.str_last_error = ''
        try:
            layer_names = [l.GetName() for l in ogr.Open(fileName)]
        except Exception as e:
            self.str_last_error = 'GDAL Error: ' + gdal.GetLastErrorMsg()
            return False
        if not siose_hr_selected:
            return self.getIsSiose(fileName, only_siose_model_layers, all_siose_model_layers)
        else:
            success, id = self.getIsSioseHr(fileName,only_siose_model_layers, all_siose_model_layers)
            return success

    def getLastError(self):
        return self.str_last_error

    def getIsSiose(self, fileName, only_siose_model_layers, all_siose_model_layers):
        self.str_last_error = ''
        try:
            layer_names = [l.GetName() for l in ogr.Open(fileName)]
        except Exception as e:
            self.str_last_error = 'GDAL Error: ' + gdal.GetLastErrorMsg()
            return False
        if only_siose_model_layers:
            for layer_name in layer_names:
                if layer_name not in self.siose_layer_names:
                    self.str_last_error = 'La capa: ' + layer_name + ' no esta incluida en SIOSE'
                    return False
        if all_siose_model_layers:
            for layer_name in self.siose_layer_names:
                if layer_name not in layer_names:
                    self.str_last_error = 'La capa: ' + layer_name + ' de SIOSE no esta en el origen'
                    return False
        return True

    def getIsSioseHr(self, fileName, only_siose_model_layers, all_siose_model_layers):
        self.str_last_error = ''
        id = None
        try:
            layer_names = [l.GetName() for l in ogr.Open(fileName)]
        except Exception as e:
            self.str_last_error = 'GDAL Error: ' + gdal.GetLastErrorMsg()
            return False, id
        if only_siose_model_layers:
            for layer_name in layer_names:
                layer_name_with_prefix = False
                for siose_hr_with_prefix in SDefs.siose_hr_layers_with_prefix:
                    if siose_hr_with_prefix == layer_name: # caso de que sea SIOSE y no SIOSE_AR
                        self.str_last_error = 'La capa: ' + layer_name + ' sin prefijo no esta incluida en SIOSE AR'
                        return False, id
                    if siose_hr_with_prefix in layer_name:
                        if not id:
                            id = layer_name.replace(siose_hr_with_prefix,'').split('_')[1]
                        layer_name_with_prefix = True
                        break
                if not layer_name_with_prefix:
                    if layer_name not in self.siose_hr_layer_names:
                        self.str_last_error = 'La capa: ' + layer_name + ' no esta incluida en SIOSE'
                        return False, id
        if all_siose_model_layers:
            for layer_name in self.siose_hr_layer_names:
                if layer_name in SDefs.siose_hr_layers_with_prefix:
                    find_layer = False
                    for file_layer_name in layer_names:
                        if layer_name == file_layer_name:
                            self.str_last_error = 'La capa: ' + layer_name + ' sin prefijo no esta incluida en SIOSE AR'
                            return False, id
                        if layer_name in file_layer_name:
                            if not id:
                                id = file_layer_name.replace(layer_name,'').split('_')[1]
                            find_layer = True
                            break
                    if not find_layer:
                        if layer_name not in layer_names:
                            self.str_last_error = 'La capa: ' + layer_name + ' de SIOSE no esta en el origen'
                            return False, id
                else:
                    if layer_name not in layer_names:
                        self.str_last_error = 'La capa: ' + layer_name + ' de SIOSE no esta en el origen'
                        return False, id
        return True, id

    def getSioseCodiigeQmlFile(self):
        return self.siose_codiige_qml_file

    def getSioseHilucsQmlFile(self):
        return self.siose_hilucs_qml_file_qml_file

    def getSioseHrCoveragesQmlFile(self):
        return self.siose_hr_coverages_qml_file

    def getSioseHrUsesQmlFile(self):
        return self.siose_hr_uses_qml_file

    def getFieldValues(self, fileName, tableName, fieldName, noDuplicated = False):
        values = []
        if not QFile.exists(fileName):
            self.str_last_error = 'No existe el fichero: ' + fileName
            return False, values
        uri = fileName + '|layername=' + tableName
        layer = QgsVectorLayer(uri,tableName,"ogr")
        if not layer.isValid():
            self.str_last_error = 'En el fichero: ' + fileName
            self.str_last_error = self.str_last_error + '\nno es valida la capa: ' + tableName
            return False, values
        if not fieldName in layer.fields().names():
            self.str_last_error = 'En el fichero: ' + fileName
            self.str_last_error = self.str_last_error + '\nen la capa: ' + tableName
            self.str_last_error = self.str_last_error + '\nno se encuentra el campo: ' + fieldName
            return False, values
        for feature in layer.getFeatures():
            value = feature[fieldName]
            if noDuplicated:
                if not value in values:
                    values.append(value)
                else:
                    values.append(value)
        return True, values

    def getFieldValuesUsingOgr(self, fileName, tableName, fieldName, noDuplicated = False):
        values = []
        if not QFile.exists(fileName):
            self.str_last_error = 'No existe el fichero: ' + fileName
            return False, values
        ds = ogr.Open(fileName)
        sql = None
        if noDuplicated:
            sql = 'SELECT DISTINCT ' + fieldName + ' FROM ' + tableName
        else:
            sql = 'SELECT ' + fieldName + ' FROM ' + tableName
        layer = ds.ExecuteSQL(sql)
        for i, feature in enumerate(layer):
            values.append(feature.GetField(0))
        # ds = None
        values.sort()
        return True, values

    def getFieldsValuesUsingOgr(self, fileName, tableName,
                                fieldsNames,
                                noDuplicated = False,
                                sortByFirstField = True):
        values = {}
        for fieldName in fieldsNames:
            values [fieldName] = []
        if not QFile.exists(fileName):
            self.str_last_error = 'No existe el fichero: ' + fileName
            return False, values
        ds = ogr.Open(fileName)
        sql = None
        sql = 'SELECT'
        if noDuplicated:
            sql += ' DISTINCT'
        cont = 0
        for fieldName in fieldsNames:
            if cont > 0:
                sql += ','
            sql += (' ' +  fieldName)
            cont = cont + 1
        sql += (' FROM ' + tableName)
        if sortByFirstField:
            sql += (' ORDER BY ' + fieldsNames[0])
        layer = ds.ExecuteSQL(sql)
        for i, feature in enumerate(layer):
            for nF in range(len(fieldsNames)):
                values[fieldsNames[nF]].append(feature.GetField(nF))
        # ds = None
        return True, values