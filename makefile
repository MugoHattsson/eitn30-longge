UP = 83
DOWN = 85

base:
	sudo python3 main.py --src hugo --dst albin --txchannel $(DOWN) --rxchannel $(UP) --isbase 1

mobile:
	sudo python3 main.py --src albin --dst hugo --txchannel $(UP) --rxchannel $(DOWN) --isbase 0

deps:
	sudo pip install -r python_deps.txt
