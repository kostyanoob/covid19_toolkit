from typing import Tuple, List, Union
import numpy as np
import yaml

from Util.numeric import floatify_string, modified_sigmoid


class RiskManager:

    def __init__(self, load_path: str = ""):
        """

        :param load_path: <str> if specified, then a yaml file will be used
        to load the configurations of the risk coefficients and discounts.
        """

        self.coeff_kind = None
        self.coeff_vector = None
        self.discount_kind = None
        self.discount_vector = None

        if load_path != "":
            self.load(load_path)

    def set_discount(self, risk_discount_kind: str, arg: Union[np.ndarray, List, str, Tuple]):
        """
        sets a discount factor vector (for custom kind) or a function (for linear and uniform kinds)
        :param risk_discount_kind: "sigmoid" or "custom" string
        :param arg: in case of a sigmoid - a 2-tuple, 2-entry list or an ndarray of length 2 (1D)
                    in case of a custom - a string, a list or a tuple...
        :return:
        """
        allowed_discount_kinds = ["custom", "sigmoid"]
        if risk_discount_kind not in allowed_discount_kinds:
            raise DiscountTypeException(
                risk_discount_kind, allowed_discount_kinds)

        if type(arg) is np.ndarray:
            if len(arg.shape) != 1:
                raise DiscountArgNdArrayShapeException(arg)
            else:
                discount_vector = arg
        elif type(arg) in [list, tuple]:
            discount_vector = np.array(arg)
        elif type(arg) is str:
            filtered_lst = filter(lambda s: s != '', arg.split(","))
            discount_vector = np.array(
                list(map(floatify_string, filtered_lst)))
        else:
            # type(arg) not in [str, list, tuple, np.ndarray]:
            raise DiscountArgTypeException(arg)

        self.discount_kind = risk_discount_kind
        if risk_discount_kind == "custom":
            self.discount_vector = discount_vector
        elif risk_discount_kind == "sigmoid":
            if len(discount_vector) != 2:
                raise DiscountArgSigmoidException(discount_vector)
            else:
                self.discount_vector = discount_vector

    def get_discount(self, time_elapsed: int) -> float:
        """
        Return a discount factor for a given "time elapsed" value
        :param time_elapsed:
        :return:
        """
        if self.discount_kind is None:
            raise ConfigurationKindException("Discount")
        elif self.discount_kind in ["custom", "sigmoid"] and self.discount_vector is None:
            raise ConfigurationArrayMissingException(
                "Discount kind", self.discount_kind)

        if self.discount_kind == "sigmoid":
            # a,b
            coefficient, shift = self.discount_vector[0], self.discount_vector[1]
            return modified_sigmoid(x=time_elapsed, coefficient=coefficient, shift=shift)
        elif self.discount_kind == "custom":
            if time_elapsed >= len(self.discount_vector):
                return 1.0
            elif time_elapsed < 0:
                return 0.0
            else:
                return self.discount_vector[time_elapsed]

    def get_discounts(self, vector_time_elapsed: Union[np.ndarray, List, Tuple]) -> Union[np.ndarray, None]:
        """
        :param vector_time_elapsed: list or 1D numpy array of values
        :return: numpy 1D array of coefficients, of a length specified by num_coefficients
                 if num_coefficients is larger than the number of "custom" exiting coefficients,
                 the missing most significant coefficients will be the replica of the
                 most significant existing coefficient. If num_coefficients is smaller than the
                 number of existing coefficients, then num_coefficients least signifficant coefficients
                 will be truncated and returned.
        """
        if type(vector_time_elapsed) is list:
            return np.array(list(map(self.get_discount, vector_time_elapsed)))
        elif type(vector_time_elapsed) is np.ndarray and 1 == len(vector_time_elapsed.shape):
            return np.apply_along_axis(self.get_discount, 0, vector_time_elapsed)
        else:
            return None

    def set_coefficients(self, risk_factor_coeff_kind: str, arg: Union[np.ndarray, List, str, Tuple, None] = None):
        """
        Sets the risk factor coefficients.
        :param risk_factor_coeff_kind: "uniform", "linear", "custom"
        :param arg: None for "linear" and for "uniform" kinds, an iterable for "custom".
                    The iterable should represent the first [0,1,2,...] values of the
                    coefficient vectors, or alternatively a string of comma separated
                    float values can be passed.
        :return:
        """
        allowed_coeff_kinds = ["linear", "uniform", "custom"]
        if risk_factor_coeff_kind not in allowed_coeff_kinds:
            raise RiskFactorCoefficientTypeException(
                risk_factor_coeff_kind, allowed_coeff_kinds)

        self.coeff_kind = risk_factor_coeff_kind
        self.coeff_vector = None
        if risk_factor_coeff_kind == "custom":
            if type(arg) is np.ndarray:
                if len(arg.shape) != 1:
                    raise RiskFactorCoefficientArgNdArrayShapeException(arg)
                else:
                    self.coeff_vector = arg
            elif type(arg) in [list, tuple]:
                self.coeff_vector = np.array(arg)
            elif type(arg) is str:
                filtered_lst = filter(lambda s: s != '', arg.split(","))
                self.coeff_vector = np.array(
                    list(map(floatify_string, filtered_lst)))
            else:
                # type(arg) not in [list, tuple, np.ndarray]:
                raise RiskFactorCoefficientArgTypeException(arg)

    def get_coefficients(self, num_coefficients: int) -> np.ndarray:
        """
        :param num_coefficients: int, specifying how many
        :return: numpy ndarray of coefficients, of a length specified by num_coefficients
                 if num_coefficients is larger than the number of "custom" exiting coefficients,
                 the missing most significant coefficients will be the replica of the
                 most significant existing coefficient.
        """
        if self.coeff_kind is None:
            raise ConfigurationKindException("Risk coefficient")
        elif self.coeff_kind == "custom" and self.coeff_vector is None:
            raise ConfigurationArrayMissingException(
                "Risk coefficient", self.coeff_kind)

        if self.coeff_kind == "linear":
            risk_factor_coefficients = np.arange(
                start=1, stop=num_coefficients + 1, step=1, dtype=np.float32)
            risk_factor_coefficients /= risk_factor_coefficients.sum()
        elif self.coeff_kind == "uniform":
            risk_factor_coefficients = np.ones(
                num_coefficients, dtype=np.float32)
            risk_factor_coefficients /= risk_factor_coefficients.sum()
        elif self.coeff_kind == "custom":
            if num_coefficients < len(self.coeff_vector):
                risk_factor_coefficients = self.coeff_vector[:num_coefficients]
            elif num_coefficients > len(self.coeff_vector):
                risk_factor_coefficients = self.coeff_vector[-1] * np.ones(
                    num_coefficients)
                risk_factor_coefficients[:len(
                    self.coeff_vector)] = self.coeff_vector
            else:
                risk_factor_coefficients = self.coeff_vector
        else:
            raise RiskFactorCoefficientTypeException(
                self.coeff_kind, ["linear", "uniform", "custom"])
        return risk_factor_coefficients

    def load(self, path: str):
        """
        load the configuration from yaml file, and set them to the current object.
        :param path: str, a path to the yaml file, containing the configurations
        """
        try:
            with open(path) as file:
                documents = yaml.full_load(file)
                self.coeff_kind = documents.get('coeff_kind', None)
                coeff_list = documents.get('coeff_vector', None)
                self.coeff_vector = np.array(
                    coeff_list) if coeff_list is not None else None
                self.discount_kind = documents.get('discount_kind', None)
                discount_list = documents.get('discount_vector', None)
                self.discount_vector = np.array(
                    discount_list) if discount_list is not None else None
        except:
            return

    def save(self, path: str):
        """
        dump the configurations (risk factors, discounts) to a yaml file
        :param path: str, a path to the yaml file, to dump the current object to
        :return:
        """
        dict_file = {}
        if self.coeff_kind is not None:
            dict_file["coeff_kind"] = self.coeff_kind
        if self.coeff_vector is not None:
            dict_file["coeff_vector"] = self.coeff_vector.tolist()
        if self.discount_kind is not None:
            dict_file['discount_kind'] = self.discount_kind
        if self.discount_vector is not None:
            dict_file["discount_vector"] = self.discount_vector.tolist()

        with open(path, 'w') as file:
            documents = yaml.dump(dict_file, file)

#################################### Exceptions ####################################


class RiskFactorCoefficientTypeException(Exception):
    def __init__(self, current, allowed):
        self.message = "Risk factor coefficient must be one of the following strings: {}. Given: \"{}\"".format(
            str(allowed), str(current))
        super().__init__(self.message)


class RiskFactorCoefficientArgTypeException(Exception):
    def __init__(self, current):
        self.message = "Risk factor coefficient argument for \"custom\" type " \
                       "must be of a type (string, tuple, list, or numpy ndarray). Given \"{}\"".format(
                           str(current))
        super().__init__(self.message)


class RiskFactorCoefficientArgNdArrayShapeException(Exception):
    def __init__(self, arg):
        self.message = "While defining risk factor coefficients for \"custom\" type " \
                       "you chose to use numpy ndarray. The array must be single dimensional, " \
                       "whereas you gave {}-dimensional array".format(
                           len(arg.shape))
        super().__init__(self.message)


class DiscountTypeException(Exception):
    def __init__(self, current, allowed):
        self.message = "Risk discount factor coefficient must be " \
                       "one of the following strings: {}. Given: {}".format(
                           str(allowed), str(current))
        super().__init__(self.message)


class DiscountArgTypeException(Exception):
    def __init__(self, current):
        self.message = "Discount argument for  " \
                       "must be of a type (string, tuple, list, or numpy ndarray). Given \"{}\"".format(
                           str(current))
        super().__init__(self.message)


class DiscountArgNdArrayShapeException(Exception):
    def __init__(self, arg):
        self.message = "While defining discount " \
                       "you chose to use numpy ndarray. The array must be single dimensional, " \
                       "whereas you gave {}-dimensional array".format(
                           len(arg.shape))
        super().__init__(self.message)


class DiscountArgSigmoidException(Exception):
    def __init__(self, arg):
        self.message = "While defining discount of a kind \"sigmoid\"" \
                       "you chose to use numpy ndarray for the argument. The array must be single dimensional, " \
                       "whereas you gave {}-dimensional array".format(
                           len(arg.shape))
        super().__init__(self.message)


class ConfigurationKindException(Exception):
    def __init__(self, message):
        self.message = message + " kind was not configured."
        super().__init__(self.message)


class ConfigurationArrayMissingException(Exception):
    def __init__(self, attr: str, kind: str):
        self.message = "{} of a kind \"{}\" kind was " \
                       "not configured with a proper array.".format(attr, kind)
        super().__init__(self.message)
