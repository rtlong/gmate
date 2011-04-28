#!/bin/bash

# Copy Plugins
if [ ! -d $HOME/.config/gedit/plugins ]; then
	mkdir -p $HOME/.local/share/gedit/plugins
fi
cp -R plugins3/* $HOME/.local/share/gedit/plugins

# Copy Styles
if [ ! -d $HOME/.config/gedit/styles ]; then
	mkdir -p $HOME/.config/gedit/styles
fi
cp styles/* $HOME/.config/gedit/styles

# Copy Language Specs
if [ ! -d $HOME/.local/share/gtksourceview-3.0/language-specs ]; then
  mkdir -p $HOME/.local/share/gtksourceview-3.0/language-specs
fi
cp lang-specs/* $HOME/.local/share/gtksourceview-3.0/language-specs/

# Copy mime types
if [ ! -d  $HOME/.local/share/mime/packages ]; then
  mkdir -p $HOME/.local/share/mime/packages
fi
cp mime/rails.xml $HOME/.local/share/mime/packages
cp mime/cfml.xml $HOME/.local/share/mime/packages

update-mime-database $HOME/.local/share/mime
