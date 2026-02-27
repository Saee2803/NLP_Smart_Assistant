class IncidentMerger:
    """
    Combines incidents from multiple OEM sources
    into a single unified incident stream.
    """

    def merge(self, *incident_lists):
        merged = []

        for lst in incident_lists:
            if not lst:
                continue
            merged.extend(lst)

        return merged

