from regex import findall

def get_params(command):
	return findall("[^\s]+", command)[1:]
