[app]
title = MasjidReceiptManager
package.name = masjidreceiptmanager
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,txt,db
version = 0.1
requirements = python3,kivy==2.3.0,pyjnius
orientation = portrait

# (list) Permissions
android.permissions = INTERNET

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (int) Target SDK version
android.api = 33

# (int) Minimum SDK version
android.minapi = 21

# (str) Android entry point, defaults to ok
android.entrypoint = org.kivy.android.PythonActivity

# (str) supported architectures
android.arch = armeabi-v7a
# include armeabi-v7a and arm64-v8a for broader device support
android.archs = armeabi-v7a, arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
