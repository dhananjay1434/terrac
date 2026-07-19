# Rebuild & Install the Android App — Exact Steps

## What this is for

The Flutter app's source code was changed (commit `1ac5a91` —
`feat(app): stamp capture_type at source for batch-anchor and farmer end-use
photos`). The APK currently on the phone was built BEFORE that change, so it
does not contain the fix. This only takes effect after a fresh build is
installed on the device.

## Before you start — checklist

1. The Android phone is connected to this computer via USB.
2. USB debugging is enabled on the phone (Settings → About phone → tap "Build
   number" 7 times → Developer options → enable "USB debugging").
3. When you plug in the phone, it will show a popup "Allow USB debugging?" —
   tap Allow / OK.
4. Run these two commands and confirm the phone shows up before doing
   anything else:

```
flutter devices
```

If the phone does not appear in the list, STOP — do not proceed to build.
Reconnect the cable, check the phone screen for the debugging prompt, and run
`flutter devices` again until it shows up.

```
adb devices
```

This should show the device with status `device` (not `unauthorized` or
`offline`). If it says `unauthorized`, look at the phone screen and tap Allow.

## Step 1 — Get a clean starting point

Run this in the project root
(`c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`):

```
flutter clean
flutter pub get
```

Wait for both to finish with no red error text before continuing.

## Step 2 — Build and install (DEBUG build — do this one)

This is the correct command for this task. It builds the app AND installs it
onto the connected phone automatically, in one step:

```
flutter run -d <device-id>
```

Replace `<device-id>` with the exact ID shown by `flutter devices` in the
checklist step above (it looks something like `ZY223JQGNQ` or similar — copy
it exactly from that output, do not guess it).

If there is only ONE device connected, you can instead run just:

```
flutter run
```

and Flutter will pick the only connected device automatically.

**What success looks like:** the terminal prints a series of build steps,
ends with something like `Syncing files to device ...` and the app opens on
the phone screen automatically. Leave the terminal window open — the app is
now running in a debug session attached to it.

**If it fails:** copy the FULL error text (do not summarize it or paraphrase
it) and stop. Do not try random fixes.

## Step 3 — Confirm it's really the new build

Once the app is open on the phone:
1. Complete one full batch capture that includes an end-use / field-application
   photo (the farmer photo step at the end of a batch).
2. This is enough — the code change is invisible in the app's UI (it only
   changes an internal data field sent during upload), so there is nothing new
   to see on screen. The change will be visible later in the web portal, in
   the Evidence section of that batch, once it syncs.

## When you're done with this debug session

Press `q` in the terminal where `flutter run` is running, or just close that
terminal window. This stops the debug session but the app STAYS installed on
the phone and keeps working normally on its own.

---

## Alternative: building a release APK instead (ONLY if asked to do this — skip otherwise)

Do not run this unless specifically told to produce a release APK file. This
project has a real signing key configured (`android/key.properties` exists),
so a release build will be properly signed — but it is a different, slower
path than Step 2 above, and produces a file you then have to manually install.

```
flutter build apk --release
```

This can take several minutes. When it finishes, the file is at:

```
build/app/outputs/flutter-apk/app-release.apk
```

To install that file onto the connected phone:

```
adb install -r "build/app/outputs/flutter-apk/app-release.apk"
```

The `-r` flag reinstalls over the existing app, keeping its data. If this
command reports an error mentioning "signatures do not match", STOP and report
that exact message back — do not uninstall the existing app to work around it,
since that would erase locally-queued unsynced data on the device.

## Rules — do not do any of these

- Do NOT run `flutter build apk` without `--release` or `--debug` and assume a
  default — always be explicit if you use the build (not run) command.
- Do NOT delete, move, or regenerate `android/key.properties` or any `.jks` /
  `.keystore` file for any reason.
- Do NOT run `adb uninstall` on the app. If a device already has this app
  installed with unsynced local data, uninstalling erases that data
  permanently before it can sync.
- Do NOT modify any source file to "fix" a build error unless the error
  message explicitly names a file and line to change AND you are told to fix
  it. Report the error instead and stop.
- Do NOT run this against more than one physical device without being told to
  — if `flutter devices` lists more than one, ask which one before proceeding.
