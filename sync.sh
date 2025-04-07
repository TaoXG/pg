#!/usr/bin/env bash

old_version=$(cat pg.version)
PACKAGE=$(ls -t ~/Downloads/Telegram\ Desktop/pg.*.zip | head -1)
mv "$PACKAGE" pg.zip
new_version=$(echo "$PACKAGE" | awk -F/ '{print $NF}' | awk -F. '{print $2}')
if [ "${new_version}" = "" ]; then
  exit
fi
echo "old version: ${old_version}  new version: ${new_version}"

if [ "${old_version}" != "${new_version}" ]; then
  echo -n "${new_version}" >pg.version
  echo "copy files"

  cp pg.version pg.zip ~/workspace/alist-tvbox/data
fi
