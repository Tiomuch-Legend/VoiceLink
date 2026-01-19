from multiprocessing import Value

def create_shared_state():
    return Value('b', False)
