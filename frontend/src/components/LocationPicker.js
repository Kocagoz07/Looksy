import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MapPin, Search, X, Plus, ChevronRight, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog';
import { ScrollArea } from './ui/scroll-area';

const API = process.env.REACT_APP_BACKEND_URL;

const LocationPicker = ({ selectedLocation, onLocationSelect, onLocationRemove }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [locations, setLocations] = useState([]);
  const [trendingLocations, setTrendingLocations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newLocation, setNewLocation] = useState({ name: '', city: '' });

  // Fetch trending locations on open
  useEffect(() => {
    if (isOpen) {
      fetchTrendingLocations();
    }
  }, [isOpen]);

  // Search locations
  useEffect(() => {
    if (searchQuery.length >= 2) {
      searchLocations();
    } else {
      setLocations([]);
    }
  }, [searchQuery]);

  const fetchTrendingLocations = async () => {
    try {
      const response = await axios.get(`${API}/api/locations/trending?limit=10`, {
        withCredentials: true
      });
      setTrendingLocations(response.data.locations || []);
    } catch (error) {
      console.error('Error fetching trending locations:', error);
    }
  };

  const searchLocations = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/api/locations/search`, {
        params: { q: searchQuery, limit: 20 },
        withCredentials: true
      });
      setLocations(response.data.locations || []);
    } catch (error) {
      console.error('Error searching locations:', error);
    } finally {
      setLoading(false);
    }
  };

  const createLocation = async () => {
    if (!newLocation.name.trim()) return;
    
    setCreating(true);
    try {
      const response = await axios.post(`${API}/api/locations`, {
        name: newLocation.name.trim(),
        city: newLocation.city.trim() || null
      }, { withCredentials: true });
      
      selectLocation(response.data);
      setNewLocation({ name: '', city: '' });
      setShowCreateForm(false);
    } catch (error) {
      console.error('Error creating location:', error);
    } finally {
      setCreating(false);
    }
  };

  const selectLocation = (location) => {
    onLocationSelect(location);
    setIsOpen(false);
    setSearchQuery('');
  };

  const removeLocation = () => {
    onLocationRemove();
  };

  // If location is selected, show it
  if (selectedLocation) {
    return (
      <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-red-500" />
          <div>
            <p className="text-sm font-medium">{selectedLocation.name}</p>
            {selectedLocation.city && (
              <p className="text-xs text-gray-500">{selectedLocation.city}</p>
            )}
          </div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={removeLocation}
          className="h-8 w-8"
        >
          <X className="w-4 h-4" />
        </Button>
      </div>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className="w-full justify-start text-gray-500 font-normal"
          data-testid="add-location-btn"
        >
          <MapPin className="w-4 h-4 mr-2" />
          Add Location
        </Button>
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MapPin className="w-5 h-5" />
            Add Location
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for a location..."
              className="pl-10"
              data-testid="location-search-input"
            />
          </div>

          <ScrollArea className="h-[300px]">
            {/* Create Custom Location */}
            {!showCreateForm ? (
              <button
                onClick={() => setShowCreateForm(true)}
                className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg text-left"
              >
                <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                  <Plus className="w-5 h-5 text-gray-600" />
                </div>
                <div>
                  <p className="font-medium text-sm">Create Custom Location</p>
                  <p className="text-xs text-gray-500">Add a new place</p>
                </div>
              </button>
            ) : (
              <div className="p-3 bg-gray-50 rounded-lg space-y-3">
                <Input
                  value={newLocation.name}
                  onChange={(e) => setNewLocation({ ...newLocation, name: e.target.value })}
                  placeholder="Location name (e.g., Central Park)"
                  data-testid="new-location-name"
                />
                <Input
                  value={newLocation.city}
                  onChange={(e) => setNewLocation({ ...newLocation, city: e.target.value })}
                  placeholder="City (optional)"
                  data-testid="new-location-city"
                />
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setShowCreateForm(false);
                      setNewLocation({ name: '', city: '' });
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={createLocation}
                    disabled={!newLocation.name.trim() || creating}
                    data-testid="create-location-btn"
                  >
                    {creating ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      'Create'
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Search Results */}
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : searchQuery.length >= 2 ? (
              <div className="mt-2">
                {locations.length === 0 ? (
                  <p className="text-center text-gray-500 py-4 text-sm">
                    No locations found for "{searchQuery}"
                  </p>
                ) : (
                  <div className="space-y-1">
                    <p className="text-xs text-gray-500 px-3 py-2">Search Results</p>
                    {locations.map((location) => (
                      <LocationItem
                        key={location.location_id}
                        location={location}
                        onSelect={() => selectLocation(location)}
                      />
                    ))}
                  </div>
                )}
              </div>
            ) : (
              /* Trending Locations */
              trendingLocations.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-gray-500 px-3 py-2">Popular Locations</p>
                  <div className="space-y-1">
                    {trendingLocations.map((location) => (
                      <LocationItem
                        key={location.location_id}
                        location={location}
                        onSelect={() => selectLocation(location)}
                      />
                    ))}
                  </div>
                </div>
              )
            )}
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Location Item Component
const LocationItem = ({ location, onSelect }) => {
  return (
    <button
      onClick={onSelect}
      className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg text-left"
      data-testid={`location-item-${location.location_id}`}
    >
      <div className="w-10 h-10 bg-red-50 rounded-full flex items-center justify-center">
        <MapPin className="w-5 h-5 text-red-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">{location.name}</p>
        {location.address?.city && (
          <p className="text-xs text-gray-500 truncate">
            {location.address.city}
            {location.address.country && `, ${location.address.country}`}
          </p>
        )}
        {location.stats?.post_count > 0 && (
          <p className="text-xs text-gray-400">
            {location.stats.post_count} {location.stats.post_count === 1 ? 'post' : 'posts'}
          </p>
        )}
      </div>
      <ChevronRight className="w-4 h-4 text-gray-400" />
    </button>
  );
};

export default LocationPicker;
