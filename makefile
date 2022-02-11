UP = 105
DOWN = 108

base:
	sudo python nrf-rxtx-test.py --src hugo --dst albin --txchannel $(DOWN) --rxchannel $(UP) --isbase 1

mobile:
	sudo python nrf-rxtx-test.py --src albin --dst hugo --txchannel $(UP) --rxchannel $(DOWN) --isbase 0

deps:
	sudo pip install -r python_deps.txt