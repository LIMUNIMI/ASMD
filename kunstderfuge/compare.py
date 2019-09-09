import pyximportcpp; pyximportcpp.install()
import test_utils
import warnings
warnings.filterwarnings('ignore')

def main():
    test_utils.full_comparison()


if __name__ == "__main__":

    main()
