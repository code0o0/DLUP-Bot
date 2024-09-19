tracker_list=$(curl -Ns https://ngosang.github.io/trackerslist/trackers_all_http.txt | awk '$0' | tr '\n\n' ',')
aria2c --max-concurrent-downloads=20 --max-upload-limit=100K --max-overall-upload-limit=1M \
       --split=10 --max-connection-per-server=10 --min-split-size=10M --disk-cache=64M \
       --enable-rpc=true --rpc-max-request-size=1024M --file-allocation=falloc --enable-mmap=false \
       --http-accept-gzip=true --max-file-not-found=0 --max-tries=20 --reuse-uri=true \
       --allow-overwrite=true --auto-file-renaming=true --check-certificate=false --optimize-concurrent-downloads=true \
       --check-integrity=true --continue=true --daemon=true --force-save=true \
       --content-disposition-default-utf8=true --quiet=true --summary-interval=0 \
       --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
       --listen-port=9003 --dht-listen-port=9003 --peer-id-prefix=-qB4520 --peer-agent=qBittorrent/4.5.2 \
       --seed-ratio=0 --seed-time=0 --bt-max-peers=128 --follow-torrent=mem \
       --bt-detach-seed-only=true --bt-remove-unselected-file=true --bt-tracker="[$tracker_list]" \
       --bt-enable-lpd=true --enable-peer-exchange=true --enable-dht=true --enable-dht6=false \
       --dht-file-path=/usr/src/app/config/dht.dat --dht-file-path6=/usr/src/app/config/dht6.dat \
       --bt-force-encryption=true --bt-require-crypto=true --bt-min-crypto-level=arc4
qbittorrent-nox -d --profile="$(pwd)"
sabnzbdplus -f sabnzbd/SABnzbd.ini -s :::9004 -b 0 -d -c -l 0 --console
