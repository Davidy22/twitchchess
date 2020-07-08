from regex import findall

def get_params(command):
	return findall("[^\s]+", command)[1:]

def process_name(x):
	return x.strip("@").casefold()
