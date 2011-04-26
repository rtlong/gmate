#!/bin/bash

# Copy Plugins
if [ ! -d $HOME/.config/gedit/plugins ]; then
	mkdir -p ~/.local/share/gedit/plugins
fi
cp -R plugins/* ~/.local/share/gedit/plugins

# Copy Styles
if [ ! -d $HOME/.config/gedit/styles ]; then
	mkdir -p ~/.config/gedit/styles
fi
cp styles/* ~/.config/gedit/styles

