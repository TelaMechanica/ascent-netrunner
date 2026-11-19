#!/bin/bash
# Build the AArch64 MAX candidate with pinned WPA Supplicant and libnl-tiny.
# Pass the input archive directory, a fresh output directory and a cross compiler.
set -euo pipefail
SRC="$1"; OUT="$2"; CC="$3"; EXTRA_CFLAGS="${4:-}"
PREFIX="${CC%-gcc}"            # e.g. aarch64-linux-gnu
AR="${PREFIX}-ar"; STRIP="${PREFIX}-strip"
RECIPE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK="$OUT/work"; SYS="$OUT/sysroot"

(
  cd "$SRC"
  sha256sum -c <<'SUMS'
20df7ae5154b3830355f8ab4269123a87affdea59fe74fe9292a91d0d7e17b2f  wpa-2.10.tar.gz
7432c9cc006900a328979d9d39d0e7018e650c0f964d6ea987d817f434e2f95f  libnl-tiny-40493a65.tar.gz
SUMS
)
mkdir "$WORK" "$SYS" "$OUT/bin"; mkdir "$SYS/lib" "$SYS/include"

# Reproducibility knobs: pin epoch, strip build-id, no host paths in output.
export SOURCE_DATE_EPOCH=1700000000
RFLAGS="-ffile-prefix-map=$WORK=. -ffile-prefix-map=$SYS=. -Wl,--build-id=none"

# --- 1. libnl-tiny -> static archive, aliased to libnl-3 / libnl-genl-3 ---
cd "$WORK"; mkdir libnl-tiny; tar xf "$SRC/libnl-tiny-40493a65.tar.gz" -C libnl-tiny --strip-components=1
cd libnl-tiny
for f in $(ls *.c | grep -v '^unl.c$'); do
  "$CC" -O2 -fPIC -ffunction-sections -fdata-sections -D_GNU_SOURCE $RFLAGS $EXTRA_CFLAGS -Iinclude -c "$f" -o "${f%.c}.o"
done
"$AR" rcsD "$SYS/lib/libnl-tiny.a" *.o          # D = deterministic archive
cp -r include/* "$SYS/include/"
cp "$SYS/lib/libnl-tiny.a" "$SYS/lib/libnl-3.a"
cp "$SYS/lib/libnl-tiny.a" "$SYS/lib/libnl-genl-3.a"

mk_config() { cat <<EOF
CONFIG_DRIVER_NL80211=y
CONFIG_LIBNL32=y
CONFIG_CTRL_IFACE=y
CONFIG_BACKEND=file
CONFIG_TLS=internal
CONFIG_INTERNAL_LIBTOMMATH=y
CONFIG_WPA2=y
CONFIG_IEEE80211N=y
CONFIG_AP=y
CFLAGS += -D_GNU_SOURCE $RFLAGS $EXTRA_CFLAGS -I$SYS/include
LIBS += -L$SYS/lib -lnl-tiny
LIBS_p += -L$SYS/lib -lnl-tiny
EOF
}
export CC LDFLAGS="-static $RFLAGS"
# --- 2. wpa_supplicant + wpa_cli ---
cd "$WORK"; tar xf "$SRC/wpa-2.10.tar.gz"; cd wpa_supplicant-2.10/wpa_supplicant
mk_config > .config
make -j4 wpa_supplicant wpa_cli >/dev/null
"$STRIP" -o "$OUT/bin/wpa_supplicant" wpa_supplicant
"$STRIP" -o "$OUT/bin/wpa_cli" wpa_cli
cp .config "$OUT/wpa_supplicant.config"
# The channel probe uses the independent ASCENT source from this repository.
"$CC" -std=gnu11 -O2 -Wall -Wextra -Werror -static \
  "$RECIPE/probe.c" -o "$OUT/bin/ascent_wifi_channels"
"$STRIP" "$OUT/bin/ascent_wifi_channels"

cd "$OUT/bin"
sha256sum wpa_supplicant wpa_cli ascent_wifi_channels
