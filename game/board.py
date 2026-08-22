class Board:
    def __init__(self, width_in, height_in, px_per_inch):
        self.width_in = width_in
        self.height_in = height_in
        self.px_per_inch = px_per_inch

    @property
    def width_px(self):
        return round(self.width_in * self.px_per_inch)

    @property
    def height_px(self):
        return round(self.height_in * self.px_per_inch)

    def to_px(self, x_in, y_in):
        return (x_in * self.px_per_inch, y_in * self.px_per_inch)

    def to_in(self, x_px, y_px):
        return (x_px / self.px_per_inch, y_px / self.px_per_inch)

    def in_to_px_len(self, length_in):
        return length_in * self.px_per_inch
