import sys
import promptbranch_cli as _impl

sys.modules[__name__] = _impl

if __name__ == '__main__':
    raise SystemExit(_impl.main())
