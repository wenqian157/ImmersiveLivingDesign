from NatNetClient import NatNetClient
import json
import urllib.request
from scipy.spatial.transform import Rotation as R
import numpy as np



def receive_new_pos(rigid_body_list):
    print(len(rigid_body_list))
    data = convert_data(rigid_body_list)
    send_to_oculus(data)

def send_to_oculus(data):
    json_str = json.dumps(data, indent=2)
    json_str = json_str.encode('utf-8')
    print(json_str)

def convert_data(rigid_body_list):
    data = []
    for i in range(len(rigid_body_list)):
        rd = rigid_body_list[i]
        pos = rd.pos
        x, y, z = quaternion_to_plane(rd.rot)

        data.append({
            "id": rd.id_num, 
            "pos": pos,
            "rot": {
                "x": x.tolist(),
                "y": y.tolist(),
                "z": z.tolist()
            },
            "quaternion": rd.rot
        })
    return data

def quaternion_to_plane(rot):
    # Convert quaternion to rotation matrix
    r = R.from_quat(rot)
    rot_matrix = r.as_matrix()

    # if flip_yz:
    #     Rxm90 = np.array([[1,0,0],
    #                 [0,0,1],
    #                 [0,-1,0]])

    #     rot_matrix = Rxm90 @ rot_matrix

    # Extract basis vectors
    x_axis = rot_matrix[:,0]
    y_axis = rot_matrix[:,1]
    z_axis = rot_matrix[:,2]

    return x_axis, y_axis, z_axis

def main():
    client = NatNetClient()
    client.pos_listener = receive_new_pos
    client.set_print_level(20)
    client.run("d")

if __name__ == "__main__":
    main()