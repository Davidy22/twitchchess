from regex import findall

def get_params(command):
	return findall("[^\s]+", command)[1:]

def process_name(x):
	return x.strip("@").casefold()

def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[:-len(suffix)]
    return s

def broadcast(poll_message, message):
	temp = poll_message.value
	if temp is None:
		poll_message.set([message])
	else:
		temp.append(message)
		poll_message.set(temp)

