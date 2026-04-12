# Launch Kea2 and load one single script quicktest.py.
adb shell rm /sdcard/monkeyq.jar
adb shell rm /sdcard/fastbot-thirdpart.jar
adb shell rm /sdcard/framework.jar

rm -r output/

cmd='kea2 run -p it.feio.android.omninotes.alpha --running-minutes 5 --max-step 30 --take-screenshots --throttle 200 --log-stamp 20250613200948-model:P2_SE-\"E2\\0253  --driver-name d unittest discover -s "$(pwd)/.." -p quicktest.py'
echo $cmd
eval $cmd

cmd='kea2 run -p it.feio.android.omninotes.alpha --running-minutes 5 --max-step 30 --take-screenshots --throttle 200 --driver-name d unittest discover -s "$(pwd)/.." -p quicktest.py'
echo $cmd
eval $cmd
