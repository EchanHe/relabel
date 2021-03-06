#!/usr/bin/python3
# -*- coding: utf-8 -*-

from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap, QImageReader, QPolygon, QImage
import os
from pathlib import Path
import json
from math import ceil
import copy
import numpy as np
import cv2
pixmap_max_size_limit = QSize(1300,700)
pixmap_min_size_limit = QSize(400,200)

rect_length_prop = 0.015
min_rect_length = 20


def convert(o):
    if isinstance(o, np.int64): return int(o)
    if isinstance(o, list): return [int(i) for i in o]
    raise TypeError

def find_hierarchy_level(hierarchy):
    level = [0] * len(hierarchy)

    for i in range(len(hierarchy)):
        level[i] = find_level(0 , i, hierarchy)
    return level

def find_level(input_level , pos, hierarchy):
    if hierarchy[pos][3] < 0 :
        return input_level
    else:
        input_level = find_level(input_level, hierarchy[pos][3], hierarchy)
        return input_level +1

def find_all_children(idx, hierarchy):
    if hierarchy[idx][2]<0:
        return None
    else:
        children = []
        children.append(hierarchy[idx][2])
        child_idx = hierarchy[idx][2]

        # Only check next kids

        while True:

            if hierarchy[child_idx][0]<0:
                break
            else:
                children.append(hierarchy[child_idx][0])

                child_idx = hierarchy[child_idx][0]

        return children

def find_neighbour(idx,  hierarchy, children):
    if hierarchy[idx][0]>=0:
        children.append(hierarchy[idx][0])
        find_neighbour(hierarchy[idx][0] , hierarchy, children)
    if hierarchy[idx][1]>=0:
        children.append(hierarchy[idx][1])
        find_neighbour(hierarchy[idx][1], hierarchy, children)



def find_children(idx, hierarchy, children):
    if hierarchy[idx][2]<0:
        return children
    else:
        if children is None:
            children = [hierarchy[idx][2]]
        else:
            children.append(hierarchy[idx][2])
        print(children)
        child_idx = hierarchy[idx][2]
        if hierarchy[child_idx][0]>=0:
            find_children(hierarchy[child_idx][0], hierarchy, children)
        if hierarchy[child_idx][1]>=0:
            find_children(hierarchy[child_idx][1], hierarchy, children)



class Segment():
    def __init__(self, segment_name,  contours = {} , hierarchy = None, error = False,info = None, absence = False):

        self.set_segment(segment_name,  contours = contours , hierarchy = hierarchy,
                         error = error,info = info, absence = absence)



    def set_segment(self, segment_name,  contours , hierarchy, error ,info , absence):
        self.segment_name = segment_name
        self.contours = contours

        self.error = error
        self.info = info
        self.absence = absence

        if hierarchy is None:
            hierarchy = [0] * len(contours)

        self.hierarchy = hierarchy

        # self.polygons = []
        self.cv_contours = []
        for _, contour in self.contours.items():
            cv_contour =np.array([[[pt['x'] , pt['y']] for pt in contour["coords"]]])
            cv_contour = cv_contour.astype(np.int32)
            self.cv_contours.append(cv_contour)
        #
        #
        # # if len(self.polygons)>1:
        # #     print(self.polygons[0].subtracted(self.polygons[1]).boundingRect())
        # #     print(self.polygons[1].subtracted(self.polygons[0]).boundingRect())
        #
        #
        # self.contours_test = []
        #
        # for contour, level, child in zip(self.contours, self.hierarchy["level"], self.hierarchy["child"]):
        #     self.contours_test.append({"coords": contour, "level":level , "child":child})


    def __mul__(self, factor):

        contours =copy.deepcopy( self.contours)
        for _, contour in contours.items():
            for coord in contour['coords']:
                coord['x'] *=factor
                coord['y'] *=factor
        # for coords in contours['coords']:
        #     for coord in coords:
        #         coord['x'] *=factor
        #         coord['y'] *=factor

        # contours['coords'] = []
        # for coords in self.contours['coords']
        #
        #     coords_new = [{"x":pt["x"] * factor, "y":pt["y"] * factor} for pt in coords]
        #
        #     contours["coords"] = coords




        return Segment(segment_name = self.segment_name, contours = contours,hierarchy = self.hierarchy,
                       error=self.error, info=self.info, absence=self.absence)


class Point():
    def __init__(self, pt_name, x, y, width = 10, error = False,info = None, absence = False):
        self.set_point(pt_name,x,y,width,error=error,info=info,absence=absence)

    def set_point(self, pt_name = None,x= None,y=None, width = None, error = None,info = None, absence = None):
        if pt_name is not None:
            self.pt_name = pt_name
        if x is not None:
            self.x = int(x)
        if absence is not None:
            self.absence = absence
        if y is not None:
            self.y = int(y)
        if error is not None:
            self.error = error

        self.info = info
        if width is None:
            width = self.rect.width()

        self.set_rect(self.x,self.y, width, width)


    def set_rect(self,cx,cy,width,height):

        x = cx - width//2
        y = cy - height//2
        self.rect = QRect(x, y, width, height)

    def check_diff(self, pt_name = None,x= None,y=None, width = None, error = None,info = None, absence = None):
        cond_name = pt_name is not None and pt_name != self.pt_name
        cond_x = x is not None and x != self.x
        cond_y = y is not None and y != self.y
        cond_absence = absence is not None and absence != self.absence
        cond_error =  error is not None and error != self.error
        cond_width = width is not None and width != self.rect.width()
        cond_info = info != self.info

        return cond_name or cond_x or cond_y or cond_absence or cond_error or cond_width or cond_info


    def __mul__(self, factor):
        new_x = self.x * factor
        new_y = self.y * factor
        new_width = self.rect.width() *factor

        return Point(self.pt_name, x=new_x, y=new_y, width=new_width, error=self.error, info=self.info, absence=self.absence)



    def get_point_props_dict(self):
        point = {'pt_name':self.pt_name,'x':self.x,'y':self.y,'absence':self.absence,'error':self.error}
        return point

    # Deprecate
    def undo_set_point(self):
        if self.cache is not None:
            self.set_point(self.cache['pt_name'], self.cache['x'], self.cache['y'],
                           error = self.cache['error'], absence = self.cache['absence'], save_cache = False)

    def set_current_cache(self,x, y):
        self.cache = self.get_point_props_dict()
        self.cache['x'] = x
        self.cache['y'] = y

class Image():
    current_pt_id = None
    current_pt_key = None
    def __init__(self, img_name, pts_list=None, segments_list = None, segments_cv_list = None, property =None):
        self.img_name = img_name
        self.attention_flag = False
        # Points
        # self.points = []
        self.points_dict = {}

        self.segments = {}


        self.label_changed = False

        if pts_list:
            for pt in pts_list:
                point = Point(pt['name'], pt['x'] , pt['y'], absence=pt.get("absence", False))
                self.points_dict[pt['name']] = point

        if segments_list:
            for segment in segments_list:
                temp = Segment(segment['name'], segment['contours'])
                self.segments[segment['name']] = temp

        if segments_cv_list:
            self.segments_cv = segments_cv_list
        else:
            self.segments_cv = {}

        ## specimen property
        self.property = property


        if len(self.points_dict)!=0:
            self.current_pt_key = list(self.points_dict.keys())[0]
        else:
            self.current_pt_key = None
        self.current_highlight_key = None


    def get_current_highlight_bbox(self, scale= None):
        if self.current_highlight_key is not None:
            if scale is not None:
                return (self.points_dict[self.current_highlight_key] * scale).rect
            else:
                return self.points_dict[self.current_highlight_key].rect
        else:
            return None
    def set_current_highlight_id(self, idx):
        self.current_highlight_id = idx

    def set_current_pt_id(self, idx):
        """
        Change the id for point
        :param idx:
        :return:
        """
        self.current_pt_id = idx

    def set_current_pt_key(self, key):
        """
        Change the id for point
        :param idx:
        :return:
        """
        self.current_pt_key = key

    def set_current_pt_key_to_start(self):
        keys = list(self.points_dict.keys())
        if keys:
            self.current_pt_key = keys[0]
        else:
            self.current_pt_key = None

    def set_current_highlight_key(self, key):

        self.current_highlight_key = key


    def set_points_width(self,width):
        for key,pt in self.points_dict.items():
            pt.set_point(width=width)


    def get_current_pt_name(self):
        return self.points_dict[self.current_pt_key].pt_name

    def get_current_pt_id(self):
        return self.current_pt_id

    def get_current_pt_key(self):
        return self.current_pt_key

    def get_current_pt(self):
        return self.points_dict[self.current_pt_key]
        # return self.points[self.current_pt_id]

    def get_curent_pt_props_dict(self):
        return self.points_dict[self.current_pt_key].get_point_props_dict()
        # return self.points[self.current_pt_id].get_point_props_dict()

class Data():
    def __init__(self, file_name = None, work_dir=None):
        """
        Init Data class (images and annotation per image)

        :param file_name: annotation file
        :param work_dir: working directory for images
        """
        self.img_size=0


        self.work_dir = work_dir

        if file_name == None:
            self.file_name = "untitled.json"
            self.no_anno_file = True
        else:
            self.file_name = file_name
            self.no_anno_file = False
        self.changed = False
        # Sorting part
        self.sort_points = False
        self.images_origin = None
        self.points_origin = None

        self.init_images()


    def init_images(self):
        self.images = []
        self.pt_names = set()
        self.seg_names = set()
        self.img_props = {}



        if self.work_dir is not None:
            # Get list of images
            extensions = ['.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
            work_dir_file_names = [os.path.basename(file_name) for file_name in Path(self.work_dir).glob('*')  if str(file_name).lower().endswith(tuple(extensions))]

            if not self.no_anno_file:
            # Has annotation file
                with open(self.file_name, "r") as read_file:
                    data = json.load(read_file)
                # Init images list
                for entry in data:
                    if entry['file_name'] in work_dir_file_names:
                        image = Image(entry['file_name'] ,
                                       entry.get('points', None),
                                      entry.get('outlines', None),
                                      entry.get("outlines_cv" , None),
                                      entry.get("property", None)
                                      )
                        self.images.append(image)
                        # Update points names of all
                        for pt in entry['points']:
                            self.pt_names.add(pt['name'])

                        #Update seg name for all seg
                        for key,_ in entry['outlines_cv'].items():
                            self.seg_names.add(key)

                        #Update outline names
                        for key,item in entry['property'].items():

                            if type(item) is str:
                                # Categorical
                                if key in self.img_props:
                                    self.img_props[key].append(item)
                                else:
                                    self.img_props[key] = [item]
                            else:
                                # Numerical
                                if key not in self.img_props:
                                    self.img_props[key] = None




            else:
            # without annotation file
                for name in work_dir_file_names:
                    image = Image(name)
                    self.images.append(image)


            self.current_image_id = 0
            self.img_size = len(self.images)
            if self.img_size !=0:
                self.current_pixmap = QPixmap(os.path.join(self.work_dir,self.get_current_image_name()))
                self.set_scale_fit_limit()

            self.filter_idx = list(range(0,self.img_size))
            self.sort_idx = list(range(0,self.img_size))
            self.flagged_img_idx= []


    def sort(self, value):
        if value == True:
            self.images_origin = self.images.copy()
            self.images.sort(key = lambda x:x.img_name, reverse = False)
        elif self.images_origin is not None:
            self.images = self.images_origin


    def set_image_id(self, idx):
        self.current_image_id = idx
        # Reset scale and current pixmap

        self.current_pixmap = QPixmap(os.path.join(self.work_dir,self.get_current_image_name()))
        self.set_scale_fit_limit()


    def set_work_dir(self,work_dir):
        self.work_dir = work_dir
        self.init_images()

    def set_file_name(self,file_name):
        self.no_anno_file = False
        self.file_name = file_name
        self.init_images()

    def set_scale(self,scale):
        temp = self.scale * scale
        if temp <= 7* self.origin_scale and temp >= self.origin_scale/2:
            self.scale=temp

    def reset_scale(self):
        self.scale = self.origin_scale

    def set_scale_fit_limit(self):

        # Setting the maximum scale limit
        if self.current_pixmap.width()>pixmap_max_size_limit.width() or self.current_pixmap.height()>pixmap_max_size_limit.height():
            width_scale = ceil(self.current_pixmap.width()/pixmap_max_size_limit.width())
            height_scale = ceil(self.current_pixmap.height()/pixmap_max_size_limit.height())

            self.origin_scale = 1/max(width_scale,height_scale)
        elif self.current_pixmap.width()<pixmap_min_size_limit.width() or self.current_pixmap.height()<pixmap_min_size_limit.height():
            width_scale = ceil(pixmap_min_size_limit.width()/self.current_pixmap.width())
            height_scale = ceil(pixmap_min_size_limit.height()/self.current_pixmap.height())

            self.origin_scale = max(width_scale,height_scale)
        else:
            self.origin_scale = 1

        self.scale = self.origin_scale
        size = self.current_pixmap.size()

        # The width length
        self.length = int(rect_length_prop * max(size.width(),size.height()))

        if self.length<min_rect_length:
            self.length = min_rect_length
        self.get_current_image().set_points_width(self.length)

    def set_current_pt_of_current_img(self, pt_name = None,x= None,y=None, error = None, absence = None,info = None, scaled_coords= False):
        if scaled_coords:
            if y is not None:
                y = int(y/self.scale)
            if x is not None:
                x = int(x/self.scale)


        if self.get_current_pt_of_current_img().check_diff(pt_name = pt_name, x= x, y=y, error = error , absence = absence,info = info):
            self.get_current_pt_of_current_img().set_point(pt_name = pt_name, x= x, y=y, error = error, absence = absence,info = info)

            self.changed = True
            return True
        else:
            return False

    def check_new_name_in_current_point_dict(self, name):
        if name in list(self.get_current_image().points_dict.keys()):
            return False
        else:
            current_key = self.get_current_image().current_pt_key

            self.get_current_image().points_dict[name] = self.get_current_image().points_dict[current_key]
            # self.get_current_image().points_dict[current_key] = None
            self.get_current_image().points_dict.pop(current_key)

            self.get_current_image().set_current_pt_key(name)

            return True

    def set_current_pt_of_current_img_dict(self, pt_prop):

        self.set_current_pt_of_current_img(pt_name = pt_prop.get('pt_name', None), x = pt_prop.get('x', None), y = pt_prop.get('y', None),
                                      absence = pt_prop.get('absence', None) , error = pt_prop.get('error', None) )


    def add_pt_for_current_img(self, pt_name, x, y, scaled_coords= True):
        """
        Add point if the name if not duplicate
        :param pt_name: pt name
        :param x: x
        :param y: y
        :param scaled_coords: if it need to scale back to real coords
        :return: If it is possible to add point
        """

        cur_pt_names = list(self.get_current_image_points().keys())
        if pt_name not in cur_pt_names:
            # if the point name is not duplicate add
            if scaled_coords:
                y = int(y/self.scale)
                x = int(x/self.scale)

            temp = Point(pt_name, x, y, width = self.length, absence=False)
            self.get_current_image().points_dict[pt_name]=temp

            self.pt_names.add(pt_name)
            self.changed = True

            return True
        else:
            return False

    def add_seg_for_current_img(self, seg_name):
        """
        Add the segmentation name
        """

        cur_seg_names = list(self.get_current_image_segments_cv().keys())
        if seg_name not in cur_seg_names:
            self.get_current_image_segments_cv()[seg_name]={"contours":None}
            self.seg_names.add(seg_name)

            return True
        else:
            return False



    # Deprecated
    def trans_current_segment_to_contour(self, segment, segment_name):
        #turn canvas into images
        image = segment.toImage()
        print(image.format())
        image = image.convertToFormat(QImage.Format_RGBA8888)
        print(image.format())
        s = image.bits().asstring(image.width()*image.height() * 4)
        arr = np.fromstring(s, dtype=np.uint8).reshape((image.height(),image.width() ,4))

        # arr_255 = np.interp(arr,[np.min(arr),np.max(arr)],[0,255]).astype(np.uint8)

        mask = arr[:,:,3]

        print(np.max(mask) , np.min(mask))

        print(arr[arr[:,:,0] !=0,:0])

        print(np.sum(arr[:,:,:3] == np.array([220,20,60])))
        _,thresh = cv2.threshold(mask,2,255,0)

        _, contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        # cv2.drawContours(arr, contours, -1, (0,255,0), 3)
        # cv2.imwrite(os.path.join("mat_test/contour" , "contour.jpg") , arr)

        segments = self.get_current_image_segments()
        # key_0 = list(segments.keys())[0]
        scale = self.origin_scale
        # example of setting 0 index outline
        segment = segments[segment_name]


        new_contours = {}
        levels = find_hierarchy_level(hierarchy[0])

        for idx, contour in enumerate(contours):
            # children = None
            # find_children(idx, hierarchy[0], children)

            children = find_all_children(idx, hierarchy[0])

            if children is not None:
                children = [int(child) for child in children]

            new_contours[str(idx)] = {"child": children,
                                      "level": levels[idx],
                                      "coords":[{"x": round(pt[0][0] / scale) ,"y": round(pt[0][1] / scale) } for  pt in contour]}

        # Turn opencv contours into relabel contour format

        segments[segment_name].set_segment(segment.segment_name, new_contours, hierarchy=None ,
                            error = segment.error , info = segment.info , absence=segment.absence)

    def trans_current_segment_to_contour_cv(self, segment, segment_name, contour_colour):
        """
        Convert the segmentaion from images to
        :param canvas:
        :param contour_name:
        :return:
        """
        image = segment.toImage()

        image = image.convertToFormat(QImage.Format_RGBA8888)

        s = image.bits().asstring(image.width()*image.height() * 4)
        arr = np.fromstring(s, dtype=np.uint8).reshape((image.height(),image.width() ,4))

        # arr_255 = np.interp(arr,[np.min(arr),np.max(arr)],[0,255]).astype(np.uint8)

        ## only the mask for the current category
        cv_colour = (contour_colour.red() , contour_colour.green() , contour_colour.blue() ,contour_colour.alpha())

        img_mask = arr[:,:,:3] != cv_colour[:3]
        mask_final = np.logical_and(img_mask[...,0], img_mask[...,1],img_mask[...,2])
        arr[mask_final,3] =0



        mask = arr[:,:,3]

        _,thresh = cv2.threshold(mask,2,255,0)


        height = self.get_current_origin_pixmap().height()
        width = self.get_current_origin_pixmap().width()

        thresh = cv2.resize(thresh,(width , height))

        _, contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)


        contours = [contour.tolist() for contour in contours]
        self.get_current_image_segments_cv()[segment_name]['contours'] = contours


    def remove_pt_for_current_img(self, key = None):
        """
        Remove the current point or point with key given


        :param idx:
        :return:
        """
        if key is None:
            key = self.get_current_image().current_pt_key
        pt = self.get_current_image_points().pop(key)


        self.get_current_image().set_current_pt_key_to_start()

        return pt

    def remove_seg_for_current_img(self, key = None):
        """
        Remove the current segmentation or segmentation with key given


        :param idx:
        :return:
        """
        if key is None:
            key = self.get_current_image().current_pt_key


        seg = self.get_current_image_segments_cv().pop(key , None)


        return seg


    def get_current_pt_of_current_img(self):
        return self.images[self.current_image_id].get_current_pt()

    def get_current_image(self):
        if self.images:
            return self.images[self.current_image_id]
        else:
            return None

    def get_current_image_points(self):
        # if self.images:
        #     return self.images[self.current_image_id].points
        # else:
        #     return None

        if self.images:
            return self.images[self.current_image_id].points_dict
        else:
            return None

    def get_current_image_segments(self):

        if self.images:
            return self.images[self.current_image_id].segments
        else:
            return None

    def get_current_image_scaled_segments(self):
        outlines = self.get_current_image_segments()

        if outlines:
            return {key : outline * self.scale for key, outline in outlines.items()}
        else:
            return None


    def get_current_image_segments_cv(self):
        if self.images:
            return self.images[self.current_image_id].segments_cv
        else:
            return None


    def get_current_image_name(self):
        return self.images[self.current_image_id].img_name

    def get_current_image_abs_path(self):
        path = os.path.join(self.work_dir , self.images[self.current_image_id].img_name)
        path = os.path.abspath(path)
        return path


    def get_current_scaled_pixmap(self):
        return self.current_pixmap.scaled(self.scale *  self.current_pixmap.size() , Qt.KeepAspectRatio)


    def get_current_origin_pixmap(self):
        return self.current_pixmap

    def get_current_scaled_points(self):
        if self.images:
            return [pt * self.scale for key, pt in self.get_current_image_points().items()]
        else:
            return None

    def has_images(self):
        if self.images:
            return True
        else:
            return False

    def has_points_current_image(self):
        if self.images and self.images[self.current_image_id].points_dict:
            return True
        else:
            return False

    def toggle_flag_img(self, state):
        """
        Set the data as flagged mode
        Intersect ( flag idx, self.filter_idx)

        Change the current image into first flagged image

        :param state: Flag mode is True or False
        :return: indices of flagged images
        """

        if state == True:
            self.flagged_img_idx =  [idx for idx, img in enumerate(self.images) if img.attention_flag == True]

            self.flagged_img_idx = list(set(self.filter_idx) & set(self.flagged_img_idx))

            if self.flagged_img_idx:
                self.current_image_id = self.flagged_img_idx[0]

        else:
            self.current_image_id = 0
            # self.images = self.images_backup
            # self.images_backup = None

        # if self.current_image_id >= len(self.images):
        #     self.current_image_id =len(self.images)-1
        return self.flagged_img_idx

    def filter_imgs_by_review_assist(self, filtered_dict):
        """
        Change the current image into first flagged image
        Intersect ( flag idx, self.filter_idx)

        :return: indices of ticked images.
        """
        all_idx = list(range(0,self.img_size))
        for prop_key, filtered_items in filtered_dict.items():
            filter_idx = list(np.where(np.isin(self.img_props[prop_key], filtered_items)==True)[0])
            all_idx = list(set(all_idx) & set(filter_idx))
        print("all idx",all_idx)
        self.filter_idx = all_idx
        # self.filter_idx = list(set(self.filter_idx) & set(self.flagged_img_idx))


        if self.filter_idx:
            self.current_image_id = self.filter_idx[0]
        return self.filter_idx

    def write_json(self, save_name = None):
        # Create data form to save
        image_list = []
        for image in self.images:
            entry = {'file_name': image.img_name}
            # points list
            points = []
            for key, pt in image.points_dict.items():
                pt_data = {"name": pt.pt_name, "x": pt.x, "y": pt.y, "info": pt.info,"error": pt.error, "absence": pt.absence}
                points.append(pt_data)
            entry['points'] = points



            entry['outlines_cv'] = image.segments_cv

            # Use the segmentation cv instead

            # segments = []
            # for key, seg in image.segments.items():
            # #     contour_data =
            #     seg_data = {"name": seg.segment_name, "contours": seg.contours}
            #     segments.append(seg_data)
            # entry['outlines'] = segments

            image_list.append(entry)

        if save_name is None:
            save_name = self.file_name

        with open(save_name, 'w') as write:
            json.dump(image_list, write , default=convert)

        self.changed = False


class Data_gui(Data, QObject):
    # Date object for relabel app

    # Data changed signal
    signal_data_changed = pyqtSignal(bool)
    signal_has_images = pyqtSignal()
    signal_has_undo = pyqtSignal(bool)

    # push in edit, remove and add
    undo_stack = []

    def __init__(self,   file_name = None, work_dir=None):
        Data.__init__(self,file_name,work_dir)
        QObject.__init__(self)
        # super().__init__()

        if self.images:
            self.signal_has_images.emit()


    def set_work_dir(self,work_dir):
        super().set_work_dir( work_dir)
        if self.images:
            self.signal_has_images.emit()

    def remove_pt_for_current_img(self, idx = None):
        pt = super().remove_pt_for_current_img(idx)

        self.value_change(True)
        self.push_undo({"pt_remove":pt})

        self.set_current_img_changed(True)

    def add_pt_for_current_img(self, pt_name, x, y, scaled_coords= True):
        # changed = Data.add_pt_for_current_img(self, pt_name, x, y, scaled_coords)
        changed = super().add_pt_for_current_img( pt_name, x, y, scaled_coords)

        self.value_change(changed)
        if changed:
            self.push_undo({"pt_add":pt_name})

        self.set_current_img_changed(changed)

        return changed


    def write_json(self, save_name = None):
        super().write_json(save_name)

        self.value_change(False)

    def set_current_pt_of_current_img(self, pt_name = None,x= None,y=None, error = None, absence = None,info = None,
                                      scaled_coords= False ):

        changed = super().set_current_pt_of_current_img(pt_name, x,y,error,absence,info,scaled_coords)

        self.value_change(changed)
        self.set_current_img_changed(changed)

        # if not dragging and changed:
        #     self.push_undo({"edit":prev_pt})

    def cache_for_dragging(self, begin):

        if begin:
            self.prev_pt = copy.deepcopy(self.get_current_pt_of_current_img())
        else:
            cur_pt = self.get_current_pt_of_current_img()
            if cur_pt.x!= self.prev_pt.x or cur_pt.y!= self.prev_pt.y:
                self.push_undo({"pt_edit":self.prev_pt})

    def undo_act(self):
        """
        React to undo different action from the poped item

        :return:
        """
        act = self.pop_undo()
        if act:
            print(act)

            key = list(act.keys())[0]
            value = act[key]

            if key == 'pt_add':
                self.remove_pt_for_current_img(value)
                self.pop_undo()

            elif key == 'pt_edit':
                key = value.pt_name
                self.get_current_image().set_current_pt_key(key)
                self.set_current_pt_of_current_img(x = value.x , y =value.y)


            elif key == 'pt_remove':
                self.get_current_image().points_dict[value.pt_name] = value

            #After undo things, clean again.


    def set_image_id(self, idx):
        if idx != self.current_image_id:
            self.undo_stack = []
            self.signal_has_undo.emit(False)

        super().set_image_id(idx)

    def push_undo(self, item):
        if len(self.undo_stack) == 0:
            self.signal_has_undo.emit(True)
        if len(self.undo_stack)<5:
            self.undo_stack.append(item)



    def pop_undo(self):
        if not self.undo_stack:
            self.signal_has_undo.emit(False)
            return False
        else:
            act = self.undo_stack.pop()

            if not self.undo_stack:
                self.signal_has_undo.emit(False)

            return act

    def value_change(self, changed):
        self.signal_data_changed.emit(changed)

    def set_changed(self, value):
        self.changed = value
        self.value_change(value)

    def set_current_img_changed(self,value):
        self.get_current_image().label_changed = value
