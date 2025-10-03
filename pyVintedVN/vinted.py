from pyVintedVN.items import Items
from pyVintedVN.requester import requester as requester_class


class Vinted:
    """
    This class is built to connect with the Vinted API.

    It serves as a wrapper around the Items class, providing a convenient interface
    for searching Vinted listings with optional proxy support.

    Each Vinted instance creates its OWN requester with independent proxy,
    ensuring no race conditions between parallel workers.

    Attributes:
        items (Items): An instance of the Items class for searching Vinted listings.
        requester: Dedicated requester instance for this Vinted object.

    Example:
        >>> vinted = Vinted()
        >>> items = vinted.items.search("https://www.vinted.fr/catalog?search_text=shoes")
    """

    def __init__(self):
        """
        Initialize the Vinted class with a DEDICATED requester instance.
        
        This ensures each Vinted (and thus each worker) has its own:
        - HTTP session
        - Proxy configuration
        - Request counter
        
        No shared state = no race conditions!

        Args: None
        """

        # Create a DEDICATED requester for THIS Vinted instance
        self.requester = requester_class(debug=True)
        
        # Initialize Items instance and pass our dedicated requester
        self.items = Items(requester=self.requester)