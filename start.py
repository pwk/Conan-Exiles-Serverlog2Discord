from subprocess import Popen

while True:
	print("Conan Exiles Serverlog is started")
	p = Popen("py serverlog.py", shell=True)
	p.wait()