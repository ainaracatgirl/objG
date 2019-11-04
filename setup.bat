@echo off
title objG Setup Wizard
echo JDev's objG language installer.
echo By using this installer you agree to the License
echo.
echo Preparing...
set/p name=Project name: 
set/p author=Author: 
set/p namespace=Namespace: 
echo Creating files...
mkdir %name%
echo author: %author% > %name%\config.yml
echo main: %namespace%/main.ghp >> %name%\config.yml
mkdir %name%\%namespace%
echo print "Hello World!" > %name%\%namespace%\main.ghp
echo Completed!
