# Feature: App Icon
**Phase:** UI Overhaul | **Status:** complete

## What It Does
Custom adaptive launcher icon: white medical cross with a RED→YELLOW→GREEN arc below it, on a deep navy (#0A1628) background. Monochrome variant (cross only) for Android 13+ themed icons.

## Key Files
- `android/app/src/main/res/drawable/ic_launcher_foreground.xml` — cross + triage arc vector
- `android/app/src/main/res/drawable/ic_launcher_background.xml` — navy background
- `android/app/src/main/res/drawable/ic_launcher_monochrome.xml` — single-tone cross
- `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml` — adaptive icon manifest

## How to Test
Build APK and install on device. Check home screen and app drawer for icon. On Android 13+ device, enable themed icons in settings.

## Known Limitations
No PNG mipmap fallbacks generated (not required — minSdk=26 guarantees adaptive icon support on all target devices).
