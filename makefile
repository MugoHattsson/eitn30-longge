base:
	sudo python nrf-rxtx-test.py --src hugo --dst albin --txchannel 75 --rxchannel 77 --isbase 1

mobile:
	sudo python nrf-rxtx-test.py --src albin --dst hugo --txchannel 77 --rxchannel 75 --isbase 0

deps:
	sudo pip install -r python_deps.txt