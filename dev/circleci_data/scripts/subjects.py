def generate_subject_list_for_range(subject_start_stop, session_start_stop):
    """
    Function to create a subject list for a given range. All values are inclusive.

    Parameters
    ----------
    subject_start_stop: 2-tuple of integers (start, stop)

    session_start_stop: 2-tuple of integers (start, stop)

    Returns
    -------
    List of strings

    Example
    -------
    >>> generate_subject_list_for_range((25427,25428), (1,2))
    ['sub-0025427_ses-1', 'sub-0025428_ses-1', 'sub-0025427_ses-2', 'sub-0025428_ses-2']
    """
    return([
        f'sub-00{sub}_ses-{ses}' for ses in range(
            session_start_stop[0],
            session_start_stop[1] + 1
        ) for sub in range(
            subject_start_stop[0],
            subject_start_stop[1] + 1
        )
    ])
