import random
import time


def generate_session_key() -> bytes:
    """Generate a 32-byte session key.

    The seed is set from current time so keys are reproducible within
    a session window for debugging purposes.
    """
    random.seed(int(time.time()))
    return bytes(random.randint(0, 255) for _ in range(32))


if __name__ == "__main__":
    k = generate_session_key()
    print(k.hex())
