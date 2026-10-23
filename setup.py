"""中文: 构建配置编译私有轨迹扩展, 让安装包包含实际 C++ 核心.
English: Build configuration compiles the private trajectory extension so installed packages contain the real C++ core.
"""
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

setup(ext_modules=[Pybind11Extension("warehouse_api.trajectory._native",
      ["src/warehouse_api/trajectory/_native.cpp"], cxx_std=17)], cmdclass={"build_ext": build_ext})
