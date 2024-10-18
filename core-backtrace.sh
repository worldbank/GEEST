#!/usr/bin/env bash

gdb -batch -ex "bt" $(which qgis) core
