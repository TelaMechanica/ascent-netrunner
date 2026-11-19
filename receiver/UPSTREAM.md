# Netrunner MAX build inputs

The source archive pins in the build script are exact. The recipe retains its
build objects, configuration and static libraries in the build directory.

- WPA Supplicant 2.10 uses the upstream source and its bundled license notices.
  The archive URL and SHA-256 are recorded in the source manifest.
- libnl-tiny uses commit `40493a655d8caa2ccf5206dde1e733abe2920432`.
  The source tree hash and exact archive hash are recorded with the recipe.
- The reference build uses Ubuntu AArch64 GCC 13.3.0 and cross glibc
  `2.39-0ubuntu8cross1`. Retain their package provenance with a release.

The link reports that glibc name-service calls may need runtime libraries even
in a static build. Receiver qualification must cover the shipped client and
control paths before this candidate replaces the dynamic MAX payload.
