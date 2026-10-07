import ast
import sys
import random
import os

iterations = 4


# ---------------------------------------------------------------------------
# UTILIDADES DE AST
# ---------------------------------------------------------------------------

def get_libraries(file):
    """Devuelve las líneas de import ORIGINALES (con alias) del archivo."""
    with open(file, "r", encoding="utf-8", errors="replace") as f:
        source = f.read()
    tree = ast.parse(source, filename=file)

    lines = []
    for node in tree.body:  # solo imports de nivel superior
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            lines.append(ast.unparse(node))
    return lines


def code_without_libraries(file):
    """Devuelve el código original sin imports de nivel superior."""
    with open(file, "r", encoding="utf-8", errors="replace") as f:
        source = f.read()
    tree = ast.parse(source, filename=file)

    tree.body = [n for n in tree.body
                 if not isinstance(n, (ast.Import, ast.ImportFrom))]
    return ast.unparse(tree)


# ---------------------------------------------------------------------------
# UTILIDADES VARIAS
# ---------------------------------------------------------------------------

def generate_prime_number():
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        return True

    while True:
        num = random.randint(1000, 1000000)
        if is_prime(num):
            return num


def random_string(length=30):
    chars = [chr(random.randint(65, 90)) for _ in range(length // 3)]
    chars += [chr(random.randint(97, 122)) for _ in range(length - len(chars))]
    random.shuffle(chars)
    return ''.join(chars)


def mod_exp(base, exp, mod):
    result = 1
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        base = (base * base) % mod
        exp //= 2
    return result


def extended_gcd(a, b):
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_s % b


# ---------------------------------------------------------------------------
# MÉTODOS DE ENCRIPTACIÓN
# ---------------------------------------------------------------------------
# REGLA DE ORO: TODO se cifra sobre BYTES (UTF-8), nunca sobre caracteres.
# Eso evita UnicodeDecodeError cuando el código tiene acentos/ñ/emoji.
# ---------------------------------------------------------------------------

def encryption_metode_1(code_to_encode):
    """Sustitución afín sobre bytes. Siempre biyectiva porque prime es impar."""
    code_bytes = code_to_encode.encode("utf-8")

    prime_number = generate_prime_number()
    salt = random.randint(1, 300)

    ct = [(prime_number * b + salt) % 256 for b in code_bytes]
    encrypted_message = ''.join(hex(i)[2:].zfill(2) for i in ct)
    decrypt_func = random_string()

    out = []
    out.append(f"def {decrypt_func}(prime_number, crypted_msg, salt):")
    out.append("    encryptedlist = [int(crypted_msg[i:i+2], 16) for i in range(0, len(crypted_msg), 2)]")
    out.append("    table = {((prime_number * char + salt) % 256): char for char in range(256)}")
    out.append("    recovery2 = bytes([table[num] for num in encryptedlist])")
    out.append("    return recovery2.decode('utf-8')")
    out.append("")
    out.append(f"_salt = {salt}")
    out.append(f"_prime_number = {prime_number}")
    out.append(f"_encrypted_message = {repr(encrypted_message)}")
    out.append(f"_decrypted = {decrypt_func}(_prime_number, _encrypted_message, _salt)")
    out.append("exec(compile(_decrypted, '<decrypted>', 'exec'))")
    return "\n".join(out)


def encryption_metode_2(code_to_encode):
    """Permutación XOR + salt sobre bytes."""
    code_bytes = code_to_encode.encode("utf-8")

    salt = random.randint(50, 500)
    key = random.randint(10, 250)
    shuffle_key = list(range(256))
    random.shuffle(shuffle_key)
    reverse_key = {v: k for k, v in enumerate(shuffle_key)}

    encoded_bytes = bytearray()
    for b in code_bytes:
        transformed = (shuffle_key[(b ^ key) % 256] + salt) % 256
        encoded_bytes.append(transformed)

    encrypted_message = ''.join(hex(i)[2:].zfill(2) for i in encoded_bytes)
    decrypt_func = random_string()

    out = []
    out.append(f"def {decrypt_func}(encrypted_message, key, salt, reverse_key):")
    out.append("    encrypted_bytes = [int(encrypted_message[i:i+2], 16) for i in range(0, len(encrypted_message), 2)]")
    out.append("    decrypted_bytes = bytes(reverse_key[(b - salt) % 256] ^ key for b in encrypted_bytes)")
    out.append("    return decrypted_bytes.decode('utf-8')")
    out.append("")
    out.append(f"_key = {key}")
    out.append(f"_salt = {salt}")
    out.append(f"_reverse_key = {repr(reverse_key)}")
    out.append(f"_encrypted_message = {repr(encrypted_message)}")
    out.append(f"_decrypted = {decrypt_func}(_encrypted_message, _key, _salt, _reverse_key)")
    out.append("exec(compile(_decrypted, '<decrypted>', 'exec'))")
    return "\n".join(out)


def encryption_metode_3(code):
    """RSA con tabla precalculada sobre bytes (0-255)."""
    code_bytes = code.encode("utf-8")

    prime1 = generate_prime_number()
    prime2 = generate_prime_number()
    n = prime1 * prime2
    phi = (prime1 - 1) * (prime2 - 1)
    e = 65537

    # Asegurar que e y phi son coprimos
    intentos = 0
    while extended_gcd(e, phi) == 0 and intentos < 10:
        prime1 = generate_prime_number()
        prime2 = generate_prime_number()
        n = prime1 * prime2
        phi = (prime1 - 1) * (prime2 - 1)
        intentos += 1

    d = extended_gcd(e, phi)

    # Tabla de descifrado para todos los bytes posibles
    decrypt_table = {}
    for ch in range(256):
        c = mod_exp(ch, e, n)
        decrypt_table[c] = ch

    encrypted_values = [mod_exp(b, e, n) for b in code_bytes]
    encrypted_hex = ','.join(str(i) for i in encrypted_values)
    decrypt_func = random_string()

    out = []
    out.append(f"def {decrypt_func}(encrypted, table):")
    out.append("    return bytes([table[int(c)] for c in encrypted.split(',')]).decode('utf-8')")
    out.append("")
    out.append(f"_table = {repr(decrypt_table)}")
    out.append(f"_encrypted_code = {repr(encrypted_hex)}")
    out.append(f"_decrypted = {decrypt_func}(_encrypted_code, _table)")
    out.append("exec(compile(_decrypted, '<decrypted>', 'exec'))")
    return "\n".join(out)


def encryption_metode_4(code):
    """XOR con clave rotativa de 16 bytes."""
    code_bytes = code.encode("utf-8")

    def rs():
        return "func_" + ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=8))

    key = [random.randint(1, 255) for _ in range(16)]
    encrypted_values = [b ^ key[i % len(key)] for i, b in enumerate(code_bytes)]
    decrypt_func = rs()

    out = []
    out.append(f"def {decrypt_func}(encrypted, key):")
    out.append("    return bytes([encrypted[i] ^ key[i % len(key)] for i in range(len(encrypted))]).decode('utf-8')")
    out.append("")
    out.append(f"_encrypted_code = {repr(encrypted_values)}")
    out.append(f"_key = {repr(key)}")
    out.append(f"_decrypted = {decrypt_func}(_encrypted_code, _key)")
    out.append("exec(compile(_decrypted, '<decrypted>', 'exec'))")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# ORQUESTACIÓN
# ---------------------------------------------------------------------------

def encrypt(original_code, iterations):
    crypted = original_code
    print(f"Iteraciones: {iterations}\n")
    for i in range(iterations):
        t = random.randint(1, 4)
        if t == 1:
            crypted = encryption_metode_1(crypted)
            print(f"  [{i+1}/{iterations}] método 1 aplicado")
        elif t == 2:
            crypted = encryption_metode_2(crypted)
            print(f"  [{i+1}/{iterations}] método 2 aplicado")
        elif t == 3:
            crypted = encryption_metode_3(crypted)
            print(f"  [{i+1}/{iterations}] método 3 aplicado")
        else:
            crypted = encryption_metode_4(crypted)
            print(f"  [{i+1}/{iterations}] método 4 aplicado")

        # Verificación temprana: si no compila, lo sabemos ya
        try:
            compile(crypted, "<ofuscado>", "exec")
        except SyntaxError as e:
            print(f"\n!! El código ofuscado NO compila tras la iteración {i+1}: {e}")
            print("   Abortando para no dejarte un archivo roto.")
            sys.exit(1)

    return crypted


def save_output_into_file(file_name, encrypted_content, import_lines):
    with open(file_name, "w", encoding="utf-8") as f:
        for line in import_lines:
            f.write(line + "\n")
        if not any("import random" in l for l in import_lines):
            f.write("import random\n")
        f.write("\n")
        f.write(encrypted_content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ofuscador.py archivo.py [iteraciones]")
        sys.exit(1)

    file_py = sys.argv[1]
    if len(sys.argv) >= 3:
        iterations = int(sys.argv[2])

    import_lines = get_libraries(file_py)
    original_code = code_without_libraries(file_py)

    print(f"Imports detectados: {import_lines}")
    print(f"Código original: {len(original_code)} chars\n")

    crypted_code = encrypt(original_code, iterations)

    out_name = os.path.basename(file_py)
    save_output_into_file(out_name, crypted_code, import_lines)
    print(f"\n✅ Guardado en {out_name}")