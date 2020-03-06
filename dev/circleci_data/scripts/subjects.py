from string import ascii_lowercase


def fmriprep_sub(sub):
    """
    Function to convert a string from f"sub-{sub_number}_ses-{ses_number}" to
    f"sub-{sub_number}{ses_letter}"

    Parameter
    ---------
    sub: str

    Returns
    -------
    fmriprep_sub: str

    Example
    -------
    >>> print(fmriprep_sub("sub-0025427_ses-1"))
    sub-0025427a
    """
    return(f"{sub.split('_')[0]}{ascii_lowercase[int(sub[-1])-1]}")


def generate_subject_list_for_range(subject_start_stop, session_start_stop=None):
    """
    Function to create a subject list for a given range. All values are inclusive.

    Parameters
    ----------
    subject_start_stop: 2-tuple of integers (start, stop) or list of specific values

    session_start_stop: 2-tuple of integers (start, stop) or list of specific values or None

    Returns
    -------
    List of strings

    Example
    -------
    >>> generate_subject_list_for_range((25427,25428), (1,2))
    ['sub-0025427_ses-1', 'sub-0025428_ses-1', 'sub-0025427_ses-2', 'sub-0025428_ses-2']
    """
    return([
        f'sub-00{sub}{ses_string}' for ses_string in ([
            f'_ses-{ses}' for ses in _expand_range(
                session_start_stop
            )
        ] if session_start_stop else [
            ''
        ]) for sub in _expand_range(subject_start_stop)
    ])

def _expand_range(tuple_or_list):
    """
    Function to expand an inclusive tuple to a range or return a literal list

    Parameter
    ---------
    tuple_or_list: 2-tuple of integers or list

    Returns
    -------
    list
    """
    return(
        range(
            tuple_or_list[0],
            tuple_or_list[1] + 1
        ) if all([
            isinstance(tuple_or_list, tuple),
            len(tuple_or_list)==2,
            *[isinstance(v, int) for v in tuple_or_list]
        ]) else list(tuple_or_list)
    )
