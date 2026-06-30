# `python -m haco` 실행 시 CLI로 위임한다.
from haco.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
