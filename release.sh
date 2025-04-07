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
  echo "commit file"

  scp pg.version pg.zip root@104.160.46.225:/var/www/html
#  git commit -am "update PG ${new_version}"
#  git push origin main
#  git push hub main
fi
