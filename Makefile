# export APP_P4A_SOURCE_DIR=~/workspace/p4a/
# export APP_ANDROID_JAVA_BUILD_TOOL=ant
export APP_ANDROID_ARCH=armeabi-v7a
export BUILDOZER_BUILD_DIR=.bdozer-$(APP_ANDROID_ARCH)
export BUILDOZER_BIN_DIR=./bin-$(APP_ANDROID_ARCH)

HTTP_PORT=8001

export APP_VERSION=0.10
export APP_TITLE=alcan
export APP_PACKAGE_NAME=$(APP_TITLE)
ADB=adb
P4A_URL=https://github.com/kivy/python-for-android
P4A_REV=22455346

APK=$(BUILDOZER_BIN_DIR)/$(APP_PACKAGE_NAME)-$(APP_VERSION)-debug.apk

SRCS=$(wildcard *.py img/*.png *.kv data/*.txt)

debug:
	make $(APK)

serve:
	make $(APK)
	cd $(BUILDOZER_BIN_DIR) && python3 -m http.server $(HTTP_PORT)

install: debug
	$(ADB) install -r $(APK)

run:
	buildozer android debug deploy run logcat


log:
	$(ADB) logcat | grep -C 5 python

$(APK): $(SRCS) .p4a
	buildozer $(VERBOSE) android debug

.p4a:
	git clone $(P4A_URL) .p4a && cd .p4a && git checkout $(P4A_REV)

intel: 
	make APP_ANDROID_ARCH=x86 ADB=~/genymotion/tools/adb debug

irun:
	make APP_ANDROID_ARCH=x86 ADB=~/genymotion/tools/adb debug install log

deeplclean:
	rm -rf $(BUILDOZER_BUILD_DIR)



