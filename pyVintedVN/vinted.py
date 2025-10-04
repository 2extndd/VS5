from pyVintedVN.items import Items


class Vinted:
    """
    This class is built to connect with the Vinted API.

    It serves as a wrapper around the Items class, providing a convenient interface
    for searching Vinted listings with optional proxy support.

    Attributes:
        items (Items): An instance of the Items class for searching Vinted listings.

    Example:
        >>> vinted = Vinted()
        >>> items = vinted.items.search("https://www.vinted.fr/catalog?search_text=shoes")
        
        >>> # Or with dedicated session from token pool:
        >>> vinted = Vinted(session=my_session)
        >>> items = vinted.items.search("https://www.vinted.fr/catalog?search_text=shoes")
    """

    def __init__(self, session=None):
        """
        Initialize the Vinted class.

        Args:
            session: Optional requests.Session instance with Bearer token already configured.
                     If not provided, uses global requester instance (legacy mode).
        """

        # Initialize Items instance with optional dedicated session
        self.items = Items(session=session)