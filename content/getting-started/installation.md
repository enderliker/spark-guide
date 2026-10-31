Spark is distributed as source. There is no package manager, no lockfile and no
build system beyond `make`.

## Requirements

| Requirement | Why |
| --- | --- |
| A C11 compiler (`gcc` or `clang`) | Builds the interpreter. |
| `make` | Drives the build. |
| The C math library | Used by the numeric natives. |
| OpenSSL development files | Used only by `tls_connect` and `https://`. On Debian/Ubuntu: `sudo apt install libssl-dev`. |
| `python3` | Runs the test suite and benchmarks (not needed to use the language). |

Supported hosts are Linux, macOS and WSL on Windows. The system natives
(`exec`, `list_dir`, `mkdir`, `sleep`) use POSIX APIs, so a native Windows
build is not supported; use WSL (Ubuntu is the recommended distribution).

## Build

From the repository root:

```bash
make            # builds ./spark
make test       # runs the full test suite (needs python3)
make coverage   # runs the tests and produces a gcov report
```

The build is warning-free under `-O3 -Wall -Wextra -Wpedantic`; CI additionally
builds with `-Werror`. A successful build leaves the interpreter at
`./spark`.

```bash
$ ./spark --version
Spark 0.1.0
```

::: tip Install it on your PATH
If you want to run Spark from any directory, either symlink the binary
(`ln -s "$PWD/spark" ~/.local/bin/spark`) or add the repository to your
`PATH`. The examples assume `spark` resolves to the built binary.
:::

## A first sanity check

```bash
./spark examples/hello.spark
```

```text
Hello, Spark!
This language compiles to bytecode and runs on a virtual machine written in C.
```

With no file argument, Spark opens the REPL:

```bash
./spark
```

```text
Spark 0.1.0 — type code and press Enter. 'exit' or Ctrl+D to exit.
spark> 1 + 2;
3
spark> exit
```

The REPL is covered in [Command Line and REPL](@tooling/command-line).

## Debug and sanitizer builds

The normal build is optimized. When working on the interpreter itself, build
with AddressSanitizer and UndefinedBehaviorSanitizer:

```bash
make clean
make CFLAGS="-std=c11 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Wpedantic" \
     LDFLAGS="-fsanitize=address,undefined"
python3 tests/run_tests.py
make clean && make
```

Any change to the VM, the compiler or the garbage collector is expected to pass
the suite under the sanitizers. The project's [definition of done](@appendix/roadmap)
also requires the full suite and the `fib(27)` benchmark gate.

## Platform notes

### Windows

Use WSL and follow the Linux instructions. From PowerShell:

```bash
wsl --install -d Ubuntu
```

Then inside Ubuntu install `build-essential`, `make`, `python3` and
`libssl-dev`.

### macOS

The Xcode command-line tools provide `clang` and `make`. OpenSSL is not the
system LibreSSL, so install it with Homebrew and point the build at it:

```bash
brew install openssl@3
make CFLAGS="-std=c11 -O3 -Wall -Wextra -Wpedantic -I$(brew --prefix openssl@3)/include" \
     LDFLAGS="-L$(brew --prefix openssl@3)/lib"
```

TLS and HTTPS need that include and library path; the rest of the language
builds without OpenSSL.

### Missing OpenSSL headers

If the build stops at `openssl/ssl.h`, the development package is missing:

```bash
sudo apt install libssl-dev       # Debian / Ubuntu
sudo dnf install openssl-devel    # Fedora
```

## Running without installing

Every example in this guide can be run straight from the repository:

```bash
./spark examples/fibonacci.spark
./spark examples/collections.spark
./spark examples/closures.spark
```

Program arguments become available in the global `argv` array
(`argv[0]` is the script path). For example:

```bash
./spark examples/http_client.spark https://example.com/
```

## Next step

Write and run [your first program](@getting-started/first-program).