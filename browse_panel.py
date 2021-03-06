from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import sys,os
import relabelData

from math import ceil, floor
import cv2
import timeit
import numpy as np

item_size = QSize(350,350)
icon_size = QSize(300,300)
thumbnail_size = QSize(300,300)
point_size = QSize(2,2)
class BrowsePanel(QWidget):

    def __init__(self,  data = None):
        super().__init__()

        self.initUI(data = data)

    # def __init__(self, init=True):
    #     super().__init__()
    #     self.init_for_testing()
    #     self.initUI(data = None)

    def initUI(self, data ):
        if data is not None:
            self.data = data
        self.layout = QVBoxLayout(self)

        self.widget_image_browser = QListWidget()
        self.widget_image_browser.setIconSize(item_size)

        self.widget_image_browser.setViewMode(QListView.IconMode)

        self.widget_image_browser.setFlow((QListView.LeftToRight))
        self.widget_image_browser.setResizeMode(QListView.Adjust)
        self.widget_image_browser.setSpacing(10)

        self.widget_image_browser.setMovement(QListView.Static)

        self.widget_image_browser.verticalScrollBar().valueChanged.connect(self.prepare_images)
        self.widget_image_browser.itemClicked.connect(self.trigger_check_state)
        self.widget_image_browser.itemDoubleClicked.connect(self.go_to_annotation)


        self.read_thread_1 = ReadThumbnailThread()
        self.read_thread_1.read_one_image.connect(self.add_image)

        self.read_thread_2 = ReadThumbnailThread()
        self.read_thread_2.read_one_image.connect(self.add_image)

        # self.read_img_threads = [ReadThumbnailThread([])]*3
        #
        # for thread in self.read_img_threads:
        #     thread.read_one_image.connect(self.add_image)


        self.painter = QPainter()
        self.painter.setCompositionMode(QPainter.CompositionMode_Source)

        self.layout.addWidget(self.widget_image_browser)
        self.setLayout(self.layout)

        # self.init_for_testing()
        self.init_list()

        # self.setMouseTracking(True)
        # self.resize.connect(self.sizechanged)

        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('Browse Panel')
        # self.show()

        self.setMouseTracking(True)


        self.is_icon_hide = False

    def init_for_testing(self):
        # Used for testing the widget itself.
        # file_name = 'data/data_file.json'
        # work_dir = './data/'

        file_name = 'genus.json'
        work_dir = '../plumage/data/thumbnail/'

        self.data = relabelData.Data(file_name,work_dir)

        # self.pixmap = QPixmap(os.path.join(self.data.work_dir, self.data.images[0].img_name))
        # self.orignal_size = self.pixmap.size()
        # self.pixmap = self.pixmap.scaled(thumbnail_size, aspectRatioMode=Qt.KeepAspectRatio)
        # self.state_browse = True

    def init_list(self):
        """
        Init list item without icons
        :return:
        """
        self.widget_image_browser.clear()
        images = self.data.images
        for image in images:
            # QT part
            item = QListWidgetItem()
            item.setSizeHint(item_size)
            # item.setIcon(icon)
            item.setText(image.img_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if image.attention_flag:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.widget_image_browser.addItem(item)


        self.thumbnail_list = [None] * self.data.img_size

        self.read_thread_1.work_dir = self.data.work_dir
        self.read_thread_2.work_dir = self.data.work_dir


    def reset_widget(self):
        self.init_list()

    def hide_icons(self, hide, flagged_img_idx):
        self.is_icon_hide = hide
        if hide:
            self.flagged_img_idx = flagged_img_idx
            for row in range(self.widget_image_browser.count()):
                if row not in flagged_img_idx:
                    self.widget_image_browser.item(row).setHidden(True)
                else:
                    self.widget_image_browser.item(row).setHidden(False)
        else:
            for row in range(self.widget_image_browser.count()):
                self.widget_image_browser.item(row).setHidden(False)


    def draw_points_args(self ,points_dict):
        """
        Draw keypoint based on the scale (original reso / thumbnail reso)

        :return:
        """


        scale = max(self.data.current_pixmap.width()/thumbnail_size.width(), self.data.current_pixmap.height()/thumbnail_size.height())

        pen = QPen(Qt.red, 2)
        brush = QBrush(QColor(0, 255, 255, 120))
        self.painter.setPen(pen)
        self.painter.setBrush(brush)

        if points_dict:
            for key, pt in points_dict.items():
                if not pt.absence:
                    bbox = pt.rect
                    self.painter.drawEllipse(bbox.center()/(scale), point_size.width(), point_size.height())

    def draw_seg_args(self, segments_cv):
        """
        Draw segmentations based on the scale
        :param segment_dict:
        :return:
        """

        scale = max(self.data.current_pixmap.width()/thumbnail_size.width(), self.data.current_pixmap.height()/thumbnail_size.height())

        height = int(self.data.get_current_origin_pixmap().height() /scale)
        width = int(self.data.get_current_origin_pixmap().width() /scale)

        # scaled zero
        img_cv_draw = np.zeros((height, width ,4)).astype('uint8')
        img_cv_draw = cv2.cvtColor(img_cv_draw,cv2.COLOR_BGRA2RGBA)

        # Draw the segmentations using segmentaion cv
        if segments_cv:
            for (_, item), color in zip(segments_cv.items() , self.parent().window().seg_colours):
                contour_cv = item['contours']
                self.draw_seg_cv(img_cv_draw,contour_cv , color , scale)

        image_cv_draw = QImage(img_cv_draw, img_cv_draw.shape[1],\
        img_cv_draw.shape[0], img_cv_draw.shape[1] * 4,QImage.Format_RGBA8888)

        return QPixmap(image_cv_draw)
        # self.canvas  = QPixmap(image_cv_draw)



    def draw_seg_cv(self,img_cv_draw,contour_cv,color,scale):
        """
        Draw opencv image using contours
        Convert img to qpixmap

        """
        if contour_cv is not None:
            contour_cv = [(np.array(contour, dtype='int32') //scale).astype('int32') for contour in contour_cv]
            cv_colour = (color.red() , color.green() , color.blue() ,color.alpha())
            print("cv colour in LabelPanel.draw_seg_cv" , cv_colour)
            cv2.fillPoly(img_cv_draw, contour_cv, cv_colour)
            img_cv_draw[img_cv_draw[...,3] >0 , : ] = cv_colour
######## end draw segmentation ####


    def prepare_images(self):
        """
        Action of visualiasing when scrolling.
        :return:
        """

        scroll_bar = self.widget_image_browser.verticalScrollBar()
        # Calculate images to be shown in here:
        image_count = len(self.data.images)

        if image_count!=0:
            # Calculate the current images count for the view port
            width = self.widget_image_browser.rect().size().width()
            images_per_row = floor(width/(self.widget_image_browser.item(0).sizeHint().width() + self.widget_image_browser.spacing()))


            height = self.widget_image_browser.rect().size().height()
            images_per_col =ceil(height / (self.widget_image_browser.item(0).sizeHint().height() + self.widget_image_browser.spacing()))

            img_per_viewport = images_per_row* images_per_col

            start = scroll_bar.value()
            prev_rows = ceil(start/ (self.widget_image_browser.item(0).sizeHint().height() + self.widget_image_browser.spacing()))
            prev_imgs = prev_rows * images_per_row




            start_img = prev_imgs -(images_per_row)
            start_img_id = max(0,start_img)
            end_img_id = min(image_count , start_img_id+images_per_row*(images_per_col+1))

            # Check the thumbnail cache and decide to clean cache.
            # thumbnail cache limit is 100
            thumbnail_list_size_limit =100
            thumbnail_idx_list = [idx for idx,thumbnail in enumerate(self.thumbnail_list) if thumbnail is not None]
            if len(thumbnail_idx_list)>thumbnail_list_size_limit:
                length = len(thumbnail_idx_list)
                emptied_count=0
                for idx in thumbnail_idx_list:
                    if idx < start_img or idx > end_img_id:
                        self.thumbnail_list[idx] = None
                        self.widget_image_browser.item(idx).setIcon(QIcon())
                        emptied_count+=1

                    if length - emptied_count<thumbnail_list_size_limit:
                        break



            if self.is_icon_hide:
                img_list = [self.data.images[img_id] for img_id in self.flagged_img_idx[start_img_id:end_img_id]]
                img_id_list = [img_id for img_id in self.flagged_img_idx[start_img_id:end_img_id]]
            else:
                img_list = [self.data.images[img_id] for img_id in range(start_img_id, end_img_id)]
                img_id_list = [img_id for img_id in range(start_img_id, end_img_id)]

            print("img id list", img_id_list)
            self.read_thread_1.terminate()

            self.read_thread_1.update_img_list(img_list[:len(img_list)//2], img_id_list[:len(img_list)//2] , self.widget_image_browser)
            self.read_thread_1.quit()
            self.read_thread_1.start()


            self.read_thread_2.terminate()

            self.read_thread_2.update_img_list(img_list[len(img_list)//2:], img_id_list[len(img_list)//2:] , self.widget_image_browser)
            self.read_thread_2.quit()
            self.read_thread_2.start()

    def add_image(self, args):
        """
        Draw thumbnail images, points and segmentation

        """

        pixmap = args[1]
        img_id = args[0]
        points_dict = args[2]
        segments_cv = args[3]

        # print(img_id, pixmap is not None , self.data.images[img_id].label_changed)
        if not (pixmap is None and self.data.images[img_id].label_changed == False):
            if pixmap is not None:
                self.thumbnail_list[img_id] = pixmap.copy()
            elif self.data.images[img_id].label_changed:
                pixmap = self.thumbnail_list[img_id].copy()
                self.data.images[img_id].label_changed = False

            self.painter.begin(pixmap)
            self.draw_points_args(points_dict)

            self.painter.drawPixmap(0,0,self.draw_seg_args(segments_cv))

            self.painter.end()




            pixmap = pixmap.scaled(icon_size, aspectRatioMode=Qt.KeepAspectRatio)
            icon = QIcon()
            icon.addPixmap(pixmap, QIcon.Normal, QIcon.Off)
            self.widget_image_browser.item(img_id).setIcon(icon)


    def resizeEvent(self, e):
        self.prepare_images()

    def trigger_check_state(self,item):
        """
        Put flag on images

        :param item:
        :return:
        """
        try:
            current_row = self.widget_image_browser.row(item)
            state = item.checkState()
            if  state== 0:
                self.data.images[current_row].attention_flag = False
            elif state == 2:
                self.data.images[current_row].attention_flag = True
            else:
                raise ValueError("check state error: state value:{}".format(state))
        except ValueError as ve:
            print(ve)

    def go_to_annotation(self, item):
        current_row = self.widget_image_browser.row(item)
        if self.parent():
            widget_file = self.parent().window().widget_file_list
            widget_file.setCurrentRow(current_row)

            self.parent().window().act_browse_mode.activate(QAction.Trigger)


class ReadThumbnailThread(QThread):
    read_one_image = pyqtSignal([list])

    def __init__(self, img_list=[] , img_id_list=[] , work_dir = None):
        QThread.__init__(self)
        self.img_list = img_list
        self.img_id_list = img_id_list
        self.work_dir = work_dir



    def __del__(self):
        self.wait()

    def update_img_list(self, img_list, img_id_list, widget_image_browser):
        self.img_list = img_list
        self.img_id_list = img_id_list
        self.widget_image_browser = widget_image_browser

    def run(self):
        for image, img_id in zip(self.img_list , self.img_id_list):

            points_dict = image.points_dict
            segments_cv = image.segments_cv

            if self.widget_image_browser.item(img_id).icon().isNull():
            # If the icon is NUll, read images

            # read images and draw annotation
            # Read images

                pixmap = QPixmap(os.path.join(self.work_dir, image.img_name))
                pixmap = pixmap.scaled(thumbnail_size, aspectRatioMode=Qt.KeepAspectRatio)
            else:
                pixmap = None

            self.read_one_image.emit([img_id, pixmap, points_dict,segments_cv])

            self.sleep(0.01)

if __name__ == '__main__':
    start = timeit.default_timer()

    app = QApplication(sys.argv)
    ex = BrowsePanel()

    stop = timeit.default_timer()
    ex.show()
    print('Time: ', stop - start)

    sys.exit(app.exec_())
