from sys import argv


def update_image(path, image):
    """
    Function to update a Singularity recipe to use a given Docker image

    Parameters
    ----------
    path: str
        Path to Singularity recipe

    image: str
        Docker image string, e.g., 'fcpindi/c-pac:latest-surface'
        or 'localhost:5000/fcpindi/c-pac:latest-surface'

    Returns
    -------
    None
    """
    with open(path, 'r') as pf:
        recipe = '\n'.join([
            f'From: {image}' if line.startswith(
                'From: '
            ) else line for line in pf.read().splitlines()
        ])

    with open(path, 'w') as pf:
        pf.write(recipe)


if __name__ == '__main__':
    if len(argv) != 3:
        print(
            'Usage: python3 use_local_dockerfile.py RECIPE_PATH IMAGE_STRING'
        )
    else:
        update_image(argv[1], argv[2])
