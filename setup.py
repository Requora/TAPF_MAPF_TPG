"""中文: 构建配置编译私有轨迹扩展, 让安装包包含实际 C++ 核心, 并在校验头文件改变后重编.
English: Build configuration compiles the private trajectory extension so installed packages contain the real C++ core and header edits trigger rebuilds.
"""
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

setup(ext_modules=[Pybind11Extension("warehouse_api.trajectory._native",
      ["src/warehouse_api/trajectory/_native.cpp"], cxx_std=17,
      depends=["src/warehouse_api/trajectory/_validation.hpp"])], cmdclass={"build_ext": build_ext})
