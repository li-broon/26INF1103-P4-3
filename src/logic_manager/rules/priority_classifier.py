# Turns an importance score into a priority band such as Urgent / Elevated / Routine.
class PriorityClassifier:
    # Returned if no bands were configured
    UNCLASSIFIED = "Unclassified"

    # bands maps each band name to the minimum score needed to be in it
    def __init__(self, bands):
        # Highest minimum first, so the first band that fits is the highest one that fits
        self._bands = sorted(dict(bands).items(), key=lambda band: band[1], reverse=True)

    @classmethod
    def from_config(cls, config):
        return cls(config.priority_bands)

    # A score exactly on a boundary belongs to the higher band, one below every band uses the lowest band
    def classify(self, score):
        if not self._bands:
            return self.UNCLASSIFIED
        for name, minimum in self._bands:
            if score >= minimum:
                return name
        return self._bands[-1][0]