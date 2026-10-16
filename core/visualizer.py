import cv2

def draw_detections(frame, weapons, humans):
    display_frame = frame.copy()
    
    # Draw Humans: GREEN bounding box
    for h in humans:
        cv2.rectangle(display_frame, (h.bbox.x1, h.bbox.y1), (h.bbox.x2, h.bbox.y2), (0, 255, 0), 2)
        # Person label requested if desired. We will just draw the green box for now, or add label.
        # User said "Person label if desired". Let's omit it to reduce clutter or add it simply.
        
    # Draw Weapons: RED bounding box + name + confidence
    for w in weapons:
        # Exclude "person" if the weapon model incorrectly outputs it, though user said "Detected weapons list excludes person", we will filter it in the detector or WS. Let's filter here just in case.
        if w.class_name.lower() == "person":
            continue
            
        cv2.rectangle(display_frame, (w.bbox.x1, w.bbox.y1), (w.bbox.x2, w.bbox.y2), (0, 0, 255), 2)
        
        # User facing names: Gun, Knife, Grenade, Missile, Sword
        name = w.class_name.capitalize()
        if name.lower() == "handgun" or name.lower() == "rifle" or name.lower() == "gun":
            name = "Gun"
            
        label = f"{name} {w.confidence:.2f}"
        cv2.putText(display_frame, label, (w.bbox.x1, max(0, w.bbox.y1 - 10)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    
    return display_frame
