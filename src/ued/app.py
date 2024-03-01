""" UED Centering App """
import panel as pn

from .model import Model
from .view import View
from .controller import Controller


def main():
    """ Run the UED Centering App """

    pn.extension("tabulator")
    pn.config.throttled = True

    model = Model()
    controller = Controller(model, None)
    view = View(controller)
    model.controller = controller
    controller.view = view

    controller.run()


if __name__ == "__main__":
    main()
