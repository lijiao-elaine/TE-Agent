cmake_minimum_required(VERSION 3.5.1)

project(unit_test)

# 设置项目目录结构
set(BIN_DIR ${CMAKE_SOURCE_DIR}/bin)
set(TEST_RESULTS_DIR ${CMAKE_BINARY_DIR}/test-results)
set(CMAKE_INSTALL_PREFIX ${CMAKE_SOURCE_DIR})

# 查找GTest包
find_package(GTest REQUIRED)

# Enable CTest
enable_testing()
include(CTest)

# 添加头文件搜索路径
# 假设emitterstate.h位于项目根目录下的include文件夹中
include_directories(
    ${GTEST_INCLUDE_DIRS}
    /home/lijiao/work/yaml-cpp/include
    /home/lijiao/work/yaml-cpp/src
    /usr/src/googletest/googlemock/include
)

link_directories(${GTEST_LIBRARY_DIRS})

# file(GLOB YAML_CPP_SOURCES 
#     "/home/moonlight/work/coder/CT-Agent/yaml-cpp/src/*.cpp"
# )

file(GLOB YAML_CPP_SOURCES 
    "/home/lijiao/work/yaml-cpp/src/emitterstate.cpp"
)

# 创建可执行文件
add_executable(unit_test test.cpp ${YAML_CPP_SOURCES})

# 链接库
target_link_libraries(unit_test 
    PRIVATE
        GTest::GTest 
        GTest::Main
        gmock
        pthread
)

# 设置编译结果的输出目录
set_target_properties(unit_test PROPERTIES
    CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)

# 添加测试 COMMAND ${CMAKE_INSTALL_PREFIX}/build/unit_test  
add_test(
    NAME EmitterStateTest
    COMMAND $<TARGET_FILE:unit_test>
    --gtest_output=xml:${CMAKE_BINARY_DIR}/EmitterStateTest.xml 
)
set_tests_properties(EmitterStateTest PROPERTIES
    LABELS "unit_test"
)
