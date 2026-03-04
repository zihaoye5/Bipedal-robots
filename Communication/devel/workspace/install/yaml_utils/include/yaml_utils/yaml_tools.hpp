/**
 * @file yaml_tools.hpp
 * @author Maximilien Naveau (maximilien.naveau@gmail.com)
 * @license License BSD-3-Clause
 * @copyright Copyright (c) 2019, New York University and Max Planck Gesellschaft.
 * @date 2019-09-30
 */

#pragma once

#include "yaml_utils/yaml_eigen.hpp"

namespace YAML {

/**
 * @brief helper function to safely read a yaml parameter
 *
 * @tparam YamlType
 * @param node
 * @param name
 * @return YamlType
 */
template<typename YamlType>
static YamlType ReadParameter(const YAML::Node& node, const std::string& name) {
	try {
		return node[name.c_str()].as<YamlType>();
	} catch (...) {
		throw std::runtime_error(
				"Error reading the yaml parameter [" + name + "]");
	}
}

/**
 * @brief helper function to safely read a yaml parameter
 *
 * @tparam YamlType
 * @param node
 * @param name
 * @param parameter
 */
template<typename YamlType>
static void ReadParameter(const YAML::Node& node, const std::string& name,
		YamlType& parameter, bool optional = false) {
	if (optional && !node[name.c_str()]) {
		return;
	}
	parameter = ReadParameter<YamlType>(node, name);
}

template<typename YamlType>
static void ReadParameterDefault(const YAML::Node& node, const std::string& name,
		YamlType& parameter, YamlType default_value) {
	if (!node[name.c_str()]) {
		parameter = default_value;
	} else {
        parameter = ReadParameter<YamlType>(node, name);
    }
}

/**
 * @brief helper function to safely read a yaml parameter
 *
 * @param node
 * @param name
 * @tparam YamlType
 * @param optional
 * @return YamlType
 */
template<typename YamlType>
void readParameter(const YAML::Node& node, const std::string& name,
		YamlType& parameter, bool optional = false) {
	if (optional && !node[name.c_str()]) {
		return;
	}
	try {
		parameter = node[name.c_str()].as<YamlType>();
	} catch (...) {
		if (!optional) {
			throw std::runtime_error(
					"Error reading the yaml parameter [" + name + "]");
		}
	}
}

}
